import { FrameParser, SampleClock, scalesFromInfo, IMU_AXES, IMU_NAMES, MAX_EMG } from './protocol.js';
import { StripChart } from './chart.js';
import * as store from './store.js';
import { DemoTransport } from './demo.js';
import { SerialTransport, serialSupported } from './serial.js';
import { analyzeSource, stridesCsv } from './gait.js';
import { GaitPanel } from './gaitui.js';

const $ = (id) => document.getElementById(id);
const KEY_COUNT = 18; // A0..A5, IMU A ax..gz, IMU B ax..gz
const LIVE_CAPACITY = 500 * 60;
const CHUNK_FLUSH_MS = 2000;
const SERIES = ['--series-1', '--series-2', '--series-3', '--series-4', '--series-5', '--series-6'];
const GAIT_EVERY_MS = 1000;
const GAIT_DEFAULTS = { sides: { A: 'right', B: 'left' }, distanceM: 0, windowS: 20, person: '', personStrideM: 0 };

// ---------- preferences (per-browser convenience only) ----------

const prefs = (() => {
  let p = {};
  try {
    p = JSON.parse(localStorage.getItem('mega-myoware-prefs') || '{}');
  } catch {}
  return {
    get: (k, d) => (k in p ? p[k] : d),
    set(k, v) {
      p[k] = v;
      try {
        localStorage.setItem('mega-myoware-prefs', JSON.stringify(p));
      } catch {}
    },
  };
})();

// ---------- live ring buffer ----------

class LiveBuffer {
  constructor(cap) {
    this.cap = cap;
    this.tArr = new Float64Array(cap);
    this.vArr = new Float32Array(cap * KEY_COUNT);
    this.clear();
  }
  clear() {
    this.n = 0;
    this.head = 0; // next write slot
  }
  push(t, vals) {
    this.tArr[this.head] = t;
    this.vArr.set(vals, this.head * KEY_COUNT);
    this.head = (this.head + 1) % this.cap;
    if (this.n < this.cap) this.n++;
  }
  slot(i) {
    return (this.head - this.n + i + this.cap) % this.cap;
  }
  t(i) {
    return this.tArr[this.slot(i)];
  }
  v(key, i) {
    return this.vArr[this.slot(i) * KEY_COUNT + key];
  }
  get latest() {
    return this.n ? this.t(this.n - 1) : 0;
  }
}

// ---------- recorder ----------

class Recorder {
  constructor(meta) {
    this.meta = meta;
    this.builder = new store.ChunkBuilder(1024);
    this.idx = 0;
    this.t0 = null;
    this.seq0 = 0;
    this.lastSeq = 0;
    this.lastT = 0;
    this.n = 0;
    this.chain = store.putRecording(meta).then((id) => {
      this.meta.id = id;
    });
    this.timer = setInterval(() => this.flush(), CHUNK_FLUSH_MS);
  }

  add(t, seq, s) {
    if (this.t0 === null) {
      this.t0 = t;
      this.seq0 = seq;
    }
    this.lastT = t - this.t0;
    this.lastSeq = seq - this.seq0;
    this.builder.add(this.lastT, this.lastSeq, s);
    this.n++;
    this.meta.emgMask |= s.emgMask;
    this.meta.imuMask |= s.imuMask;
    if (this.builder.full) this.flush();
  }

  summary() {
    this.meta.samples = this.n;
    this.meta.durationS = this.lastT;
    this.meta.lost = this.n ? this.lastSeq + 1 - this.n : 0;
  }

  flush() {
    if (!this.builder.n) return this.chain;
    const chunk = this.builder.take();
    const idx = this.idx++;
    this.summary();
    this.meta.chunks = this.idx;
    const meta = { ...this.meta };
    this.chain = this.chain
      .then(() => store.putChunk(this.meta.id, idx, chunk))
      .then(() => store.putRecording(meta))
      .catch((e) => showMessage(`Saving failed: ${e.message}. Free some disk space and keep the tab open.`, true));
    return this.chain;
  }

  async stop() {
    clearInterval(this.timer);
    this.flush();
    this.summary();
    this.meta.status = 'complete';
    this.meta.endedAt = new Date().toISOString();
    await this.chain;
    await store.putRecording({ ...this.meta });
    return this.meta;
  }
}

// ---------- state ----------

const live = new LiveBuffer(LIVE_CAPACITY);
const clock = new SampleClock();
const st = {
  transport: null,
  parser: null,
  info: null,
  scales: scalesFromInfo(null),
  recorder: null,
  recStart: 0,
  paused: false,
  window: Number(prefs.get('window', 10)),
  lastSampleAt: 0,
  rateWindow: [], // [performance.now(), received] pairs
  infoWaiter: null,
  bannerWaiter: null,
  bannerSeen: false,
  bytes: 0,
  streamAskedAt: 0,
  streamRetried: false,
  gaitDue: 0,
};

// ---------- UI helpers ----------

function showMessage(text, error = false) {
  const m = $('message');
  m.textContent = text || '';
  m.hidden = !text;
  m.classList.toggle('error', error);
}

function log(line) {
  const pre = $('log');
  const stamp = new Date().toLocaleTimeString();
  pre.textContent = `${stamp}  ${line}\n${pre.textContent}`.slice(0, 20000);
}

function setStatus(text, kind = '') {
  const s = $('status');
  s.textContent = text;
  s.className = `pill ${kind}`;
}

function fmtDuration(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function emgMaskFromUi() {
  let m = 0;
  document.querySelectorAll('#emg-mask input').forEach((cb) => {
    if (cb.checked) m |= 1 << Number(cb.value);
  });
  return m;
}

// ---------- charts ----------

function emgSeries(mask) {
  const out = [];
  for (let ch = 0; ch < MAX_EMG; ch++) if (mask & (1 << ch)) out.push({ key: ch, label: `A${ch}`, color: SERIES[ch] });
  return out;
}

function imuSeries(k, gyro) {
  return [0, 1, 2].map((a) => ({
    key: 6 + k * 6 + (gyro ? 3 : 0) + a,
    label: IMU_AXES[(gyro ? 3 : 0) + a],
    color: SERIES[a],
  }));
}

function buildCharts(host, onZoom) {
  host.replaceChildren();
  const c = {
    emg: new StripChart(host, { title: 'EMG (MyoWare output)', unit: 'counts', series: emgSeries(1), minSpan: 20, onZoom }),
    accel: [],
    gyro: [],
  };
  c.emg.el.classList.add('wide');
  for (let k = 0; k < 2; k++) {
    c.accel.push(new StripChart(host, { title: `${IMU_NAMES[k]} acceleration`, unit: 'g', series: imuSeries(k, false), minSpan: 0.2, onZoom }));
    c.gyro.push(new StripChart(host, { title: `${IMU_NAMES[k]} angular rate`, unit: '°/s', series: imuSeries(k, true), minSpan: 10, onZoom }));
  }
  return c;
}

function applyMasks(c, emgMask, imuMask) {
  c.emg.setSeries(emgSeries(emgMask));
  c.emg.hidden = !emgMask;
  for (let k = 0; k < 2; k++) {
    c.accel[k].hidden = !(imuMask & (1 << k));
    c.gyro[k].hidden = !(imuMask & (1 << k));
  }
}

function drawCharts(c, src, t0, t1, gapS) {
  for (const ch of [c.emg, ...c.accel, ...c.gyro]) if (!ch.el.hidden) ch.draw(src, t0, t1, gapS);
}

const liveCharts = buildCharts($('live-charts'), null);
applyMasks(liveCharts, prefs.get('emgMask', 1), 0);

// ---------- gait analysis (live) ----------

// People's measured stride lengths, kept in this browser by name.
const people = {
  list: () => Object.entries(prefs.get('people', {})).map(([name, strideM]) => ({ name, strideM })).sort((a, b) => a.name.localeCompare(b.name)),
  save(name, strideM) {
    prefs.set('people', { ...prefs.get('people', {}), [name]: strideM });
  },
};

const liveGait = new GaitPanel($('live-gait'), {
  live: true,
  idPrefix: 'lg',
  profiles: people,
  settings: { ...GAIT_DEFAULTS, ...prefs.get('gait', {}) },
  onChange: (s) => {
    prefs.set('gait', s);
    st.gaitDue = 0;
  },
});

// Re-runs the analysis on the chosen stretch of the live buffer about once a second.
function updateLiveGait(now) {
  if (now < st.gaitDue || !live.n || $('live').hidden || st.paused) return;
  st.gaitDue = now + GAIT_EVERY_MS;
  const s = liveGait.settings;
  const t1 = live.latest;
  let t0 = t1 - (s.windowS || 60);
  if (!s.windowS && st.recorder && st.recorder.t0 !== null) t0 = st.recorder.t0;
  try {
    liveGait.render(
      analyzeSource(live, { t0, t1, imuMask: st.info ? st.info.imu_mask : 3, sides: s.sides, distanceM: s.distanceM, personStrideM: s.personStrideM, accelRangeG: 32768 / st.scales.accelLsbPerG }),
    );
  } catch (e) {
    log(`gait analysis failed: ${e.message}`);
  }
}

// ---------- EMG jack chips ----------

(function buildChips() {
  const host = $('emg-mask');
  const mask = prefs.get('emgMask', 1);
  for (let ch = 0; ch < MAX_EMG; ch++) {
    const l = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = ch;
    cb.checked = !!(mask & (1 << ch));
    const sw = document.createElement('i');
    sw.style.background = `var(${SERIES[ch]})`;
    l.append(cb, sw, `A${ch}`);
    host.append(l);
    cb.addEventListener('change', () => {
      const m = emgMaskFromUi();
      prefs.set('emgMask', m);
      applyMasks(liveCharts, m, st.info ? st.info.imu_mask : 0);
      send(`e${m}`);
    });
  }
})();

// ---------- connection ----------

async function send(cmd) {
  if (!st.transport) return;
  try {
    await st.transport.write(`${cmd}\n`);
  } catch (e) {
    log(`write failed: ${e.message}`);
  }
}

function onInfo(info) {
  st.info = info;
  st.scales = scalesFromInfo(info);
  log(`info ${JSON.stringify(info)}`);
  $('rate').value = info.rate || '';
  $('rate').max = info.max_rate || 500;
  $('rate-max').textContent = `max ${info.max_rate} Hz on ${info.port} at ${info.baud} baud`;
  applyMasks(liveCharts, info.emg_mask, info.imu_mask);
  document.querySelectorAll('#emg-mask input').forEach((cb) => {
    cb.checked = !!(info.emg_mask & (1 << Number(cb.value)));
  });
  const imus = ['A', 'B'].filter((_, k) => info.imu_mask & (1 << k));
  $('t-imu').textContent = imus.length ? imus.join(' + ') : 'none found';
  const who = (info.who || []).map((w, k) => (info.imu_mask & (1 << k) ? `${'AB'[k]} id 0x${w.toString(16)}` : `${'AB'[k]} missing`));
  $('t-imu-sub').textContent = who.join(' · ');
  $('t-link').textContent = st.transport ? st.transport.label : '–';
  $('t-link-sub').textContent = `${info.port} · ${info.baud} baud`;
  $('t-rate-sub').textContent = `target ${info.rate} Hz`;
  $('fw').textContent = `Firmware ${info.fw}`;
  if (st.infoWaiter) {
    st.infoWaiter(info);
    st.infoWaiter = null;
  }
}

function onSample(s) {
  const { seq, us } = clock.step(s);
  const t = us / 1e6;
  const sc = st.scales;
  const vals = new Float32Array(KEY_COUNT).fill(NaN); // NaN = channel off, line breaks
  for (let ch = 0; ch < MAX_EMG; ch++) vals[ch] = s.emg[ch] ?? NaN;
  for (let k = 0; k < 2; k++) {
    if (!s.imu[k] || s.flags & (1 << k)) continue;
    for (let a = 0; a < 6; a++) vals[6 + k * 6 + a] = s.imu[k][a] / (a < 3 ? sc.accelLsbPerG : sc.gyroLsbPerDps);
  }
  live.push(t, vals);
  st.lastSampleAt = performance.now();
  if (st.recorder) st.recorder.add(t, seq, s);
}

function waitForInfo(ms) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      st.infoWaiter = null;
      resolve(null);
    }, ms);
    st.infoWaiter = (info) => {
      clearTimeout(timer);
      resolve(info);
    };
  });
}

function waitForBanner(ms) {
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(timer);
      st.bannerWaiter = null;
      resolve();
    };
    const timer = setTimeout(done, ms);
    st.bannerWaiter = done;
  });
}

async function connect(transport) {
  if (st.transport) await disconnect();
  showMessage('');
  setStatus('Connecting…');
  st.parser = new FrameParser({
    onSample,
    onInfo,
    onLog: (t) => log(t),
    onText: (t) => {
      log(t);
      if (t.includes('ready')) st.bannerSeen = true;
      if (st.bannerWaiter && t.includes('ready')) st.bannerWaiter();
    },
  });
  st.bytes = 0;
  st.lastSampleAt = 0;
  st.streamAskedAt = 0;
  st.streamRetried = false;
  st.bannerSeen = false;
  transport.onBytes = (b) => {
    st.bytes += b.length;
    st.parser.push(b);
  };
  transport.onClose = (err) => {
    log(err.message);
    disconnect(err.message);
  };
  try {
    await transport.open();
  } catch (e) {
    setStatus('Not connected');
    if (e.name === 'NotFoundError') showMessage('No port was chosen. Press Connect and pick the Arduino Mega 2560 (usbmodem) entry.');
    else showMessage(`Could not open the port: ${e.message}`, true);
    log(`open failed: ${e.name} ${e.message}`);
    return;
  }
  log(`opened ${transport.detail || transport.label} at ${transport.baud} baud`);
  st.transport = transport;
  $('connect').hidden = true;
  $('demo').hidden = true;
  $('disconnect').hidden = false;

  // Opening the Mega's USB port resets it. Its bootloader restarts its wait on
  // every byte it receives, so stay quiet until the sketch prints its banner
  // (about 2 s). Bluetooth links don't reset the board and print no banner.
  if (transport.label === 'USB') {
    setStatus('Waiting for the board to restart…');
    const t0 = performance.now();
    await waitForBanner(4000);
    log(st.bannerSeen ? `board ready after ${Math.round(performance.now() - t0)} ms` : `no banner after 4 s (${st.bytes} bytes received), asking anyway`);
  }
  let info = null;
  for (let attempt = 0; attempt < 6 && !info && st.transport === transport; attempt++) {
    send('?');
    info = await waitForInfo(1000);
  }
  if (st.transport !== transport) return;
  if (!info) {
    log(`no settings frame after 6 tries; ${st.bytes} bytes received, ${st.parser.stats.crcErrors} corrupt frames`);
    setStatus('No reply', 'error');
    showMessage(
      'The port opened but the board did not answer. Check that mega_myoware_stream is flashed, that the baud matches (USB 115200; the Bluetooth module 9600 unless you changed it), and that the ZS-040 LED blinks twice every few seconds (paired).',
      true,
    );
    return;
  }
  const wantMask = prefs.get('emgMask', 1);
  if (wantMask !== info.emg_mask) send(`e${wantMask}`);
  const wantRate = prefs.get('rate', 0);
  if (wantRate) send(`r${wantRate}`);
  clock.reset();
  live.clear();
  st.rateWindow = [];
  await send('s');
  st.streamAskedAt = performance.now();
  log('asked the board to start streaming');
  setStatus('Starting stream…');
  $('record').disabled = false;
  $('rescan').disabled = false;
}

async function disconnect(reason) {
  const t = st.transport;
  st.transport = null;
  if (st.recorder) await stopRecording();
  if (t) {
    try {
      await t.close();
    } catch {}
  }
  setStatus(reason ? 'Disconnected' : 'Not connected', reason ? 'error' : '');
  if (reason) showMessage(reason, true);
  $('connect').hidden = false;
  $('demo').hidden = false;
  $('disconnect').hidden = true;
  $('record').disabled = true;
  $('rescan').disabled = true;
}

$('connect').addEventListener('click', () => {
  if (!serialSupported()) {
    $('no-serial').hidden = false;
    return;
  }
  connect(new SerialTransport({ baud: Number($('baud').value) }));
});
$('demo').addEventListener('click', () => connect(new DemoTransport({ baud: Number($('baud').value), dropRate: 0.002 })));
$('disconnect').addEventListener('click', () => disconnect());
$('baud').value = String(prefs.get('baud', 115200));
$('baud').addEventListener('change', () => prefs.set('baud', Number($('baud').value)));
$('rate-apply').addEventListener('click', () => {
  const hz = Math.round(Number($('rate').value));
  if (!(hz > 0)) return;
  prefs.set('rate', hz);
  send(`r${hz}`);
});
$('rate').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('rate-apply').click();
});
$('rescan').addEventListener('click', () => send('i'));
$('window').value = String(st.window);
$('window').addEventListener('change', () => {
  st.window = Number($('window').value);
  prefs.set('window', st.window);
});
$('pause').addEventListener('click', () => {
  st.paused = !st.paused;
  $('pause').setAttribute('aria-pressed', String(st.paused));
  $('pause').textContent = st.paused ? 'Resume view' : 'Pause view';
});
if (!serialSupported()) $('no-serial').hidden = false;

// ---------- recording ----------

async function startRecording() {
  const now = new Date();
  const name = $('rec-name').value.trim() || `Recording ${now.toLocaleString()}`;
  const info = st.info || {};
  st.recorder = new Recorder({
    name,
    notes: $('rec-notes').value.trim(),
    createdAt: now.toISOString(),
    status: 'recording',
    source: info.synthetic ? 'demo' : st.transport.label,
    rateHz: info.rate,
    emgMask: 0,
    imuMask: 0,
    scales: { ...st.scales },
    gait: structuredClone(liveGait.settings),
    device: info,
    samples: 0,
    durationS: 0,
    lost: 0,
    chunks: 0,
  });
  st.recStart = performance.now();
  $('record').classList.add('on');
  $('record-label').textContent = 'Stop';
  $('rec-elapsed').classList.add('on');
  document.querySelectorAll('#emg-mask input, #rate, #rate-apply, #rescan').forEach((el) => (el.disabled = true));
}

async function stopRecording() {
  const r = st.recorder;
  st.recorder = null;
  $('record').classList.remove('on');
  $('record-label').textContent = 'Record';
  $('rec-elapsed').classList.remove('on');
  document.querySelectorAll('#emg-mask input, #rate, #rate-apply').forEach((el) => (el.disabled = false));
  $('rescan').disabled = !st.transport;
  if (!r) return;
  const meta = await r.stop();
  $('rec-name').value = '';
  log(`saved "${meta.name}": ${meta.samples} samples, ${meta.durationS.toFixed(1)} s, ${meta.lost} lost`);
  await refreshList();
}

$('record').addEventListener('click', () => (st.recorder ? stopRecording() : startRecording()));

// ---------- live render loop ----------

function renderLive() {
  const now = performance.now();
  if (st.transport) {
    st.rateWindow.push([now, clock.received]);
    while (st.rateWindow.length > 2 && now - st.rateWindow[0][0] > 2000) st.rateWindow.shift();
    const [t0, n0] = st.rateWindow[0];
    const hz = now - t0 > 300 ? ((clock.received - n0) * 1000) / (now - t0) : 0;
    $('t-rate').textContent = hz ? hz.toFixed(hz < 50 ? 1 : 0) : '0';
    const total = clock.received + clock.lost;
    $('t-lost').textContent = clock.lost.toLocaleString();
    const crc = st.parser ? st.parser.stats.crcErrors : 0;
    $('t-lost-sub').textContent = `${total ? ((100 * clock.lost) / total).toFixed(2) : '0.00'} % · ${crc} corrupt frames`;
    if (st.lastSampleAt && now - st.lastSampleAt > 2000 && st.info) setStatus('No data for 2 s', 'error');
    else if (st.lastSampleAt) setStatus(`Streaming · ${st.transport.label}`, 'live');
    else if (st.streamAskedAt && now - st.streamAskedAt > 3000) {
      if (!st.streamRetried) {
        st.streamRetried = true;
        st.streamAskedAt = now;
        log(`no samples 3 s after asking (${st.bytes} bytes received); asking again`);
        send('s');
      } else {
        st.streamAskedAt = 0;
        setStatus('No samples', 'error');
        showMessage('The board answered but sent no samples. Open Device messages below and send those lines to the maintainer.', true);
      }
    }
    if (!st.info) $('t-link-sub').textContent = `${st.bytes || 0} bytes received`;
  }
  if (st.recorder) $('rec-elapsed').textContent = fmtDuration((now - st.recStart) / 1000);
  if (!st.paused && live.n && !$('live').hidden) {
    const t1 = live.latest;
    const period = st.info && st.info.rate ? 1 / st.info.rate : 0.01;
    drawCharts(liveCharts, live, t1 - st.window, t1, period * 3.5);
  }
  updateLiveGait(now);
  requestAnimationFrame(renderLive);
}
requestAnimationFrame(renderLive);

// ---------- recordings tab ----------

let selectedId = null;
let detail = null; // {meta, data, charts, src, t0, t1, gait, gaitResult}

function recordingSource(meta, d) {
  const sc = meta.scales || scalesFromInfo(null);
  return {
    n: d.n,
    t: (i) => d.t[i],
    v: (key, i) => {
      if (key < 6) return d.emg[i * 6 + key];
      if (d.flags[i] & (key < 12 ? 1 : 2)) return NaN; // IMU read failed
      const a = (key - 6) % 6;
      return d.imu[i * 12 + key - 6] / (a < 3 ? sc.accelLsbPerG : sc.gyroLsbPerDps);
    },
  };
}

async function refreshList() {
  const rows = await store.listRecordings();
  $('rec-count').textContent = rows.length ? String(rows.length) : '';
  $('rec-empty').hidden = rows.length > 0;
  const body = $('rec-rows');
  body.replaceChildren(
    ...rows.map((r) => {
      const tr = document.createElement('tr');
      tr.tabIndex = 0;
      tr.setAttribute('aria-selected', String(r.id === selectedId));
      const name = document.createElement('td');
      name.textContent = r.name;
      if (r.status !== 'complete') {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = r.status === 'recording' && st.recorder && st.recorder.meta.id === r.id ? 'recording now' : 'interrupted, kept up to last save';
        name.append(tag);
      }
      const when = document.createElement('td');
      when.textContent = new Date(r.createdAt).toLocaleString();
      const len = document.createElement('td');
      len.className = 'num';
      len.textContent = fmtDuration(r.durationS || 0);
      const lost = document.createElement('td');
      lost.className = 'num';
      lost.textContent = (r.lost || 0).toLocaleString();
      tr.append(name, when, len, lost);
      const open = () => openRecording(r.id);
      tr.addEventListener('click', open);
      tr.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          open();
        }
      });
      return tr;
    }),
  );
  if (selectedId && !rows.some((r) => r.id === selectedId)) {
    selectedId = null;
    $('rec-detail').hidden = true;
  }
}

async function openRecording(id) {
  selectedId = id;
  document.querySelectorAll('#rec-rows tr').forEach((tr) => tr.setAttribute('aria-selected', 'false'));
  const meta = await store.getRecording(id);
  const data = await store.loadSamples(id);
  await refreshList();
  const zoom = (a, b) => {
    detail.t0 = a ?? 0;
    detail.t1 = b ?? Math.max(detail.src.n ? data.t[data.n - 1] : 1, 0.001);
    drawDetail();
  };
  const charts = buildCharts($('d-charts'), zoom);
  applyMasks(charts, meta.emgMask, meta.imuMask);
  detail = { meta, data, charts, src: recordingSource(meta, data), t0: 0, t1: data.n ? Math.max(data.t[data.n - 1], 0.001) : 1 };
  const gait = new GaitPanel($('d-gait'), {
    live: false,
    idPrefix: 'dg',
    profiles: people,
    settings: { ...GAIT_DEFAULTS, ...prefs.get('gait', {}), ...(meta.gait || {}) },
    onZoom: zoom,
    onChange: async (s) => {
      if (!detail || detail.gait !== gait) return;
      detail.meta.gait = s;
      runDetailGait();
      await store.putRecording(detail.meta);
    },
  });
  gait.hidden = !meta.imuMask;
  gait.strideCsv.addEventListener('click', () => {
    if (detail && detail.gaitResult) download(`${safeName(detail.meta.name)}.gait.csv`, new Blob([stridesCsv(detail.gaitResult, detail.meta.name)], { type: 'text/csv' }));
  });
  detail.gait = gait;
  if (meta.imuMask) runDetailGait();
  $('rec-detail').hidden = false;
  $('d-name').textContent = meta.name;
  const rate = data.n > 1 ? (data.n - 1) / (data.t[data.n - 1] || 1) : 0;
  $('d-meta').textContent = [
    new Date(meta.createdAt).toLocaleString(),
    `${fmtDuration(meta.durationS)} (${(meta.durationS || 0).toFixed(2)} s)`,
    `${data.n.toLocaleString()} samples`,
    `${rate.toFixed(1)} Hz measured`,
    `${(meta.lost || 0).toLocaleString()} lost`,
    meta.source,
  ].join(' · ');
  $('d-notes').textContent = meta.notes || '';
  requestAnimationFrame(drawDetail);
}

function runDetailGait() {
  const { meta, src, gait } = detail;
  const s = gait.settings;
  try {
    const accelRangeG = 32768 / (meta.scales || scalesFromInfo(null)).accelLsbPerG;
    detail.gaitResult = analyzeSource(src, { imuMask: meta.imuMask, sides: s.sides, distanceM: s.distanceM, personStrideM: s.personStrideM, accelRangeG });
    gait.render(detail.gaitResult);
    gait.draw(detail.t0, detail.t1);
  } catch (e) {
    showMessage(`Gait analysis failed: ${e.message}`, true);
  }
}

function drawDetail() {
  if (!detail || $('recordings').hidden) return;
  const rate = detail.meta.rateHz || 100;
  drawCharts(detail.charts, detail.src, detail.t0, detail.t1, 3.5 / rate);
  if (detail.gait) detail.gait.draw(detail.t0, detail.t1);
}

$('d-reset').addEventListener('click', () => {
  if (!detail) return;
  detail.t0 = 0;
  detail.t1 = detail.data.n ? Math.max(detail.data.t[detail.data.n - 1], 0.001) : 1;
  drawDetail();
});

function download(name, blob) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

const safeName = (s) => s.replace(/[^\w.-]+/g, '_').replace(/^_+|_+$/g, '') || 'recording';

export function toCsv(meta, d) {
  const sc = meta.scales || scalesFromInfo(null);
  const emg = [];
  for (let ch = 0; ch < 6; ch++) if (meta.emgMask & (1 << ch)) emg.push(ch);
  const imus = [0, 1].filter((k) => meta.imuMask & (1 << k));
  const head = ['time_s', 'seq', 'flags'];
  for (const ch of emg) head.push(`A${ch}_counts`, `A${ch}_volts`);
  for (const k of imus)
    for (const a of IMU_AXES) head.push(`imu${'AB'[k]}_${a}_${a[0] === 'a' ? 'g' : 'dps'}`);
  const lines = [
    `# ${meta.name}`,
    `# started ${meta.createdAt}; rate ${meta.rateHz} Hz; source ${meta.source}; firmware ${(meta.device && meta.device.fw) || '?'}`,
    `# volts = counts * ${sc.adcRefV} / 1023; flags bit0/bit1 = IMU A/B read failed (values 0)`,
    head.join(','),
  ];
  const parts = [lines.join('\n') + '\n'];
  let buf = [];
  for (let i = 0; i < d.n; i++) {
    const row = [d.t[i].toFixed(6), d.seq[i], d.flags[i]];
    for (const ch of emg) {
      const c = d.emg[i * 6 + ch];
      row.push(c, ((c * sc.adcRefV) / 1023).toFixed(4));
    }
    for (const k of imus)
      for (let a = 0; a < 6; a++) row.push((d.imu[i * 12 + k * 6 + a] / (a < 3 ? sc.accelLsbPerG : sc.gyroLsbPerDps)).toFixed(a < 3 ? 5 : 3));
    buf.push(row.join(','));
    if (buf.length === 5000) {
      parts.push(buf.join('\n') + '\n');
      buf = [];
    }
  }
  if (buf.length) parts.push(buf.join('\n') + '\n');
  return new Blob(parts, { type: 'text/csv' });
}

$('d-csv').addEventListener('click', () => {
  if (detail) download(`${safeName(detail.meta.name)}.csv`, toCsv(detail.meta, detail.data));
});

$('d-backup').addEventListener('click', () => {
  if (!detail) return;
  const { meta, data } = detail;
  const backup = {
    format: 'mega-myoware-recording',
    version: 1,
    meta: { ...meta, id: undefined },
    n: data.n,
    t: Array.from(data.t),
    seq: Array.from(data.seq),
    flags: Array.from(data.flags),
    emg: Array.from(data.emg),
    imu: Array.from(data.imu),
  };
  download(`${safeName(meta.name)}.backup.json`, new Blob([JSON.stringify(backup)], { type: 'application/json' }));
});

$('d-rename').addEventListener('click', async () => {
  if (!detail) return;
  const name = prompt('Recording name', detail.meta.name);
  if (name === null) return;
  const notes = prompt('Notes', detail.meta.notes || '');
  detail.meta.name = name.trim() || detail.meta.name;
  if (notes !== null) detail.meta.notes = notes.trim();
  await store.putRecording(detail.meta);
  $('d-name').textContent = detail.meta.name;
  $('d-notes').textContent = detail.meta.notes || '';
  await refreshList();
});

$('d-delete').addEventListener('click', async () => {
  if (!detail) return;
  if (!confirm(`Delete "${detail.meta.name}" from this browser? Download a backup first if you may need it.`)) return;
  await store.deleteRecording(detail.meta.id);
  detail = null;
  selectedId = null;
  $('rec-detail').hidden = true;
  await refreshList();
});

$('import').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  e.target.value = '';
  if (!file) return;
  try {
    const b = JSON.parse(await file.text());
    if (b.format !== 'mega-myoware-recording') throw new Error('not a recording backup from this app');
    const meta = { ...b.meta, status: b.meta.status || 'complete', importedAt: new Date().toISOString() };
    delete meta.id;
    const id = await store.putRecording(meta);
    const chunk = {
      n: b.n,
      t: Float64Array.from(b.t),
      seq: Uint32Array.from(b.seq),
      flags: Uint8Array.from(b.flags),
      emg: Uint16Array.from(b.emg),
      imu: Int16Array.from(b.imu),
    };
    await store.putChunk(id, 0, chunk);
    await store.putRecording({ ...meta, id, chunks: 1 });
    await refreshList();
    openRecording(id);
  } catch (err) {
    alert(`Could not import ${file.name}: ${err.message}`);
  }
});

// ---------- tabs ----------

function showTab(name) {
  for (const t of ['live', 'recordings']) {
    $(`tab-${t}`).setAttribute('aria-selected', String(t === name));
    $(t).hidden = t !== name;
  }
  if (name === 'recordings') refreshList().then(() => requestAnimationFrame(drawDetail));
}
$('tab-live').addEventListener('click', () => showTab('live'));
$('tab-recordings').addEventListener('click', () => showTab('recordings'));
window.addEventListener('resize', () => requestAnimationFrame(drawDetail));
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => requestAnimationFrame(drawDetail));

// A recording left in "recording" state by a closed tab is kept as interrupted.
(async () => {
  try {
    for (const r of await store.listRecordings())
      if (r.status === 'recording') await store.putRecording({ ...r, status: 'interrupted' });
    await refreshList();
  } catch (e) {
    showMessage(`This browser blocked local storage, so recordings cannot be saved here: ${e.message}`, true);
  }
})();

window.addEventListener('beforeunload', (e) => {
  if (st.recorder) {
    st.recorder.flush();
    e.preventDefault();
  }
});
