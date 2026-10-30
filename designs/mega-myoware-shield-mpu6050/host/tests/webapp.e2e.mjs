// Browser test of the web app with Playwright (Chromium).
//   node designs/mega-myoware-shield-mpu6050/host/tests/webapp.e2e.mjs [screenshot-dir]
// Serves ../../web, then:
//   1. streams from the built-in demo, records ~3 s, checks the saved
//      recording, its CSV export and a backup/import round trip;
//   1b. records ~11 s of the demo's synthetic walk and checks the gait
//      parameters live, on the saved recording, and in the gait CSV;
//   2. replaces navigator.serial with a fake port that answers like the
//      sketch (including the ~2 s silence after a USB reset) to exercise the
//      real Web Serial code path;
//   3. checks phone width has no horizontal scroll, in light and dark.
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '..', '..', 'web');
const shots = process.argv[2];
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require('playwright'));
} catch {
  ({ chromium } = await import('playwright'));
}

const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
const server = createServer(async (req, res) => {
  const path = join(webRoot, decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/\/$/, '/index.html'));
  try {
    const body = await readFile(path);
    res.writeHead(200, { 'content-type': types[extname(path)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${server.address().port}/`;
if (shots) await mkdir(shots, { recursive: true });

const browser = await chromium.launch();
const errors = [];
const watch = (page) => {
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
};
const num = async (page, id) => Number((await page.textContent(`#${id}`)).replace(/[^\d.]/g, ''));

try {
  // ---- 1. demo stream, record, review, export, backup/import ----
  const ctx = await browser.newContext({ viewport: { width: 1360, height: 1000 }, acceptDownloads: true });
  const page = await ctx.newPage();
  watch(page);
  await page.goto(url);
  await page.click('#demo');
  await page.waitForFunction(() => document.querySelector('#status').textContent.startsWith('Streaming'));
  await page.waitForTimeout(1500);
  const hz = await num(page, 't-rate');
  assert.ok(hz > 150, `demo rate ${hz} Hz`);
  // two EMG jacks
  await page.check('#emg-mask input[value="2"]');
  await page.waitForFunction(() => document.querySelector('#rate-max').textContent.includes('max'));
  await page.fill('#rec-name', 'e2e walk');
  await page.fill('#rec-notes', 'synthetic');
  await page.click('#record');
  await page.waitForTimeout(3200);
  await page.hover('#live-charts canvas', { position: { x: 400, y: 80 } });
  if (shots) await page.screenshot({ path: join(shots, 'live-light.png'), fullPage: true });
  await page.click('#record');
  await page.waitForFunction(() => document.querySelector('#rec-count').textContent === '1');
  await page.click('#tab-recordings');
  await page.click('#rec-rows tr');
  await page.waitForFunction(() => !document.querySelector('#rec-detail').hidden && document.querySelector('#d-meta').textContent.includes('samples'));
  const meta = await page.textContent('#d-meta');
  const samples = Number(meta.match(/([\d,]+) samples/)[1].replace(/,/g, ''));
  assert.ok(samples > 450, `saved ${samples} samples`);
  // drag-zoom on the EMG chart
  const box = await page.locator('#d-charts canvas').first().boundingBox();
  await page.mouse.move(box.x + 120, box.y + 60);
  await page.mouse.down();
  await page.mouse.move(box.x + 420, box.y + 60, { steps: 5 });
  await page.mouse.up();
  await page.mouse.move(box.x + 300, box.y + 80);
  if (shots) await page.screenshot({ path: join(shots, 'recording-light.png'), fullPage: true });

  const [csvDl] = await Promise.all([page.waitForEvent('download'), page.click('#d-csv')]);
  const csv = await readFile(await csvDl.path(), 'utf8');
  const lines = csv.trim().split('\n');
  const header = lines.find((l) => l.startsWith('time_s'));
  assert.equal(
    header,
    'time_s,seq,flags,A0_counts,A0_volts,A2_counts,A2_volts,imuA_ax_g,imuA_ay_g,imuA_az_g,imuA_gx_dps,imuA_gy_dps,imuA_gz_dps,imuB_ax_g,imuB_ay_g,imuB_az_g,imuB_gx_dps,imuB_gy_dps,imuB_gz_dps',
  );
  const rows = lines.filter((l) => !l.startsWith('#') && l !== header);
  assert.equal(rows.length, samples);
  const mag = rows.map((r) => Math.hypot(...r.split(',').slice(7, 10).map(Number)));
  const sortedMag = mag.slice().sort((a, b) => a - b);
  const medMag = sortedMag[sortedMag.length >> 1];
  assert.ok(medMag > 0.9 && medMag < 1.1, `IMU A |accel| median ${medMag} g`);
  assert.ok(sortedMag[sortedMag.length - 1] > 1.3, 'IMU A sees the walk');

  const [bkDl] = await Promise.all([page.waitForEvent('download'), page.click('#d-backup')]);
  const backupPath = await bkDl.path();
  await page.setInputFiles('#import', backupPath);
  await page.waitForFunction(() => document.querySelector('#rec-count').textContent === '2');
  const meta2 = await page.textContent('#d-meta');
  assert.ok(meta2.includes(`${samples.toLocaleString('en-US')} samples`), meta2);

  page.once('dialog', (d) => d.accept());
  await page.click('#d-delete');
  await page.waitForFunction(() => document.querySelector('#rec-count').textContent === '1');
  await page.click('#tab-live');
  await page.click('#disconnect');
  await ctx.close();

  // ---- 1b. gait analysis, live and on a saved recording ----
  {
    const gctx = await browser.newContext({ viewport: { width: 1360, height: 1000 }, acceptDownloads: true });
    const gp = await gctx.newPage();
    watch(gp);
    await gp.goto(url);
    await gp.selectOption('#lg-window', '0'); // since Record was pressed
    await gp.fill('#lg-distance', '10');
    await gp.dispatchEvent('#lg-distance', 'change');
    await gp.click('#demo');
    await gp.waitForFunction(() => document.querySelector('#status').textContent.startsWith('Streaming'));
    await gp.fill('#rec-name', 'e2e gait');
    await gp.click('#record');
    // the demo stands for 1.5 s, then walks 12 strides of ~1.1 s
    await gp.waitForTimeout(11000);
    const tileVal = (host, label) =>
      gp.evaluate(
        ([h, l]) => {
          const t = [...document.querySelectorAll(`${h} .gait-tiles .tile`)].find((x) => x.querySelector('.label').textContent === l);
          return Number(t.querySelector('strong').textContent);
        },
        [host, label],
      );
    const liveCad = await tileVal('#live-gait', 'Cadence');
    assert.ok(liveCad > 100 && liveCad < 118, `live cadence ${liveCad}`);
    const liveStance = await gp.textContent('#live-gait .gait-tiles .tile:nth-child(5) strong');
    assert.match(liveStance, /^6\d \/ 3\d$/, `stance/swing ${liveStance}`);
    if (shots) await gp.screenshot({ path: join(shots, 'gait-live.png'), fullPage: true });
    await gp.click('#record');
    await gp.waitForFunction(() => document.querySelector('#rec-count').textContent === '1');
    await gp.click('#tab-recordings');
    await gp.click('#rec-rows tr');
    await gp.waitForFunction(() => document.querySelectorAll('#d-gait .strides tbody tr').length > 0);
    const rowsN = await gp.locator('#d-gait .strides tbody tr').count();
    assert.ok(rowsN >= 12, `${rowsN} strides in the recording (both legs)`);
    assert.equal(await gp.inputValue('#dg-distance'), '10', 'walk distance saved with the recording');
    const recLen = await tileVal('#d-gait', 'Mean stride length');
    assert.ok(recLen > 0.4 && recLen < 2, `Eq. 4 stride length ${recLen}`);
    const sensorLen = await gp.evaluate(() => {
      const row = [...document.querySelectorAll('#d-gait .gait-table tbody tr')].find((r) => r.querySelector('th').textContent.startsWith('Stride length, sensor'));
      return Number(row.lastElementChild.textContent.split(' ')[0]);
    });
    assert.ok(Math.abs(sensorLen - 1.2) < 0.12, `sensor stride length ${sensorLen} (demo walks 1.2 m strides)`);
    await gp.click('#d-gait .strides summary');
    if (shots) await gp.screenshot({ path: join(shots, 'gait-recording.png'), fullPage: true });
    const [gDl] = await Promise.all([gp.waitForEvent('download'), gp.click('#dg-csv')]);
    const gcsv = (await readFile(await gDl.path(), 'utf8')).trim().split('\n');
    assert.ok(gcsv[1].startsWith('leg,imu,stride,hs_s'));
    assert.equal(gcsv.length - 2, rowsN);
    // changing a leg re-runs the analysis and is saved
    await gp.selectOption('#dg-side-B', 'off');
    await gp.waitForFunction(() => document.querySelectorAll('#d-gait .gait-table thead th').length === 3);
    await gctx.close();
  }

  // ---- 2. fake Web Serial port that behaves like the sketch over USB ----
  const ctx2 = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page2 = await ctx2.newPage();
  watch(page2);
  await page2.addInitScript(() => {
    const written = [];
    window.__serialWrites = written;
    const port = {
      opts: null,
      getInfo: () => ({ usbVendorId: 0x2341, usbProductId: 0x0042 }),
      async open(opts) {
        this.opts = opts;
        const { DemoTransport } = await import('/demo.js');
        const dev = new DemoTransport({ baud: opts.baudRate });
        let ctrl;
        this.readable = new ReadableStream({ start: (c) => (ctrl = c) });
        dev.onBytes = (b) => ctrl.enqueue(b);
        // A USB open resets the Mega. Its stk500v2 bootloader waits ~1 s for
        // an upload and starts again on every byte it receives, so the sketch
        // (and its banner) only starts once the line has been quiet for 1 s,
        // and never sooner than 1.6 s after the open.
        const openedAt = performance.now();
        let lastRx = openedAt;
        const boot = setInterval(() => {
          const now = performance.now();
          if (now - openedAt > 1600 && now - lastRx > 1000) {
            clearInterval(boot);
            dev.open();
          }
        }, 50);
        this.writable = new WritableStream({
          // Real serial writes complete asynchronously; a second getWriter()
          // while one is pending throws, as in Chrome.
          write: async (chunk) => {
            await new Promise((r) => setTimeout(r, 15));
            const text = new TextDecoder().decode(chunk);
            written.push(text);
            if (dev.timer) dev.write(text);
            else lastRx = performance.now(); // swallowed by the bootloader
          },
        });
        this.dev = dev;
      },
      async close() {
        await this.dev.close();
      },
    };
    Object.defineProperty(navigator, 'serial', { value: { requestPort: async () => port } });
  });
  await page2.goto(url);
  // A saved jack choice makes connect() send e<mask> right before s.
  await page2.check('#emg-mask input[value="1"]');
  await page2.click('#connect');
  await page2.waitForFunction(() => document.querySelector('#status').textContent.startsWith('Streaming'), null, { timeout: 10000 });
  await page2.waitForTimeout(1200);
  assert.ok((await num(page2, 't-rate')) > 150);
  assert.equal(await page2.textContent('#t-link'), 'USB');
  const writes = await page2.evaluate(() => window.__serialWrites.join(''));
  assert.ok(writes.includes('?\n') && writes.includes('s\n'), JSON.stringify(writes));
  await page2.fill('#rate', '50');
  await page2.click('#rate-apply');
  await page2.waitForFunction(() => document.querySelector('#t-rate-sub').textContent === 'target 50 Hz');
  await page2.waitForTimeout(2500);
  const slow = await num(page2, 't-rate');
  assert.ok(slow > 40 && slow < 60, `rate after r50: ${slow}`);
  await page2.click('#disconnect');
  await page2.waitForFunction(() => window.__serialWrites.join('').includes('x\n'), null, { timeout: 2000 });
  await ctx2.close();

  // ---- 3. phone width, light and dark ----
  for (const scheme of ['light', 'dark']) {
    const ctx3 = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: scheme, isMobile: true, hasTouch: true });
    const p = await ctx3.newPage();
    watch(p);
    await p.goto(url);
    await p.click('#demo');
    await p.waitForTimeout(1500);
    const overflow = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    assert.equal(overflow, 0, `${scheme} phone overflow ${overflow}px`);
    if (shots) await p.screenshot({ path: join(shots, `phone-${scheme}.png`), fullPage: true });
    if (scheme === 'dark') {
      await p.setViewportSize({ width: 1360, height: 1000 });
      await p.waitForTimeout(400);
      if (shots) await p.screenshot({ path: join(shots, 'live-dark.png') });
    }
    await ctx3.close();
  }

  assert.deepEqual(errors, []);
  console.log('webapp e2e: all checks passed');
} finally {
  await browser.close();
  server.close();
}
