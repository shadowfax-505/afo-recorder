// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/coherence.test.mjs
// Coherence between two simulated raw EMG channels with a known common drive.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyzeRawCoherence, coherence, confidenceLimit, fft, highpass, phaseWindows, rawPair } from '../../web/coherence.js';
import { rng } from '../../web/gaitsim.js';

const FS = 2000;

function gauss(r) {
  return Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r());
}

// Band-limited noise: sum of tones with random phase, unit RMS.
function bandNoise(n, lo, hi, r, tones = 40) {
  const ts = Array.from({ length: tones }, () => ({ w: (2 * Math.PI * (lo + (hi - lo) * r())) / FS, p: 2 * Math.PI * r() }));
  const k = Math.sqrt(2 / tones);
  return Float64Array.from({ length: n }, (_, i) => k * ts.reduce((s, t) => s + Math.sin(t.w * i + t.p), 0));
}

// Two "EMG" channels: independent wide-band carriers (interference pattern)
// whose amplitude follows 1 + depth * drive, where drive is a common 20-30 Hz
// rhythm. Offset 2048 counts, like MyoWare RAW at mid-supply.
function pairWithDrive(seconds, depth, seed, mains = 0) {
  const r = rng(seed);
  const n = seconds * FS;
  const drive = bandNoise(n, 20, 30, r);
  const x = new Float64Array(n);
  const y = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const m = Math.max(0, 1 + depth * drive[i]);
    const hum = mains * Math.sin((2 * Math.PI * 50 * i) / FS);
    x[i] = Math.round(2048 + 150 * m * gauss(r) + hum);
    y[i] = Math.round(2048 + 120 * m * gauss(r) + hum);
  }
  return { x, y };
}

test('FFT matches a direct transform and inverts', () => {
  const r = rng(1);
  const n = 64;
  const re = Float64Array.from({ length: n }, () => r() - 0.5);
  const im = new Float64Array(n);
  const src = Float64Array.from(re);
  fft(re, im);
  for (const k of [0, 3, 17, 32]) {
    let a = 0;
    let b = 0;
    for (let i = 0; i < n; i++) {
      a += src[i] * Math.cos((2 * Math.PI * k * i) / n);
      b -= src[i] * Math.sin((2 * Math.PI * k * i) / n);
    }
    assert.ok(Math.abs(re[k] - a) < 1e-9 && Math.abs(im[k] - b) < 1e-9, `bin ${k}`);
  }
  fft(re, im, true);
  for (let i = 0; i < n; i++) assert.ok(Math.abs(re[i] / n - src[i]) < 1e-12);
});

test('high-pass removes the offset without a start-up step', () => {
  const x = Float64Array.from({ length: 4000 }, (_, i) => 2048 + 100 * Math.sin((2 * Math.PI * 100 * i) / FS));
  const h = highpass(x, 20, FS);
  assert.ok(Math.abs(h[0]) < 110 && Math.abs(h[3999]) < 110);
  const mean = h.reduce((s, v) => s + v, 0) / h.length;
  assert.ok(Math.abs(mean) < 0.5, `mean ${mean}`);
  const rms = Math.sqrt(h.slice(500, 3500).reduce((s, v) => s + v * v, 0) / 3000);
  assert.ok(Math.abs(rms - 100 / Math.SQRT2) < 2, `rms ${rms}`); // 100 Hz passes untouched
});

test('a common 20-30 Hz drive shows as coherence in that band only', () => {
  const { x, y } = pairWithDrive(60, 0.6, 7);
  const c = coherence(x, y, FS);
  assert.equal(c.L, Math.floor((60 * FS) / 512));
  assert.ok(Math.abs(c.cl95 - confidenceLimit(c.L)) < 1e-12);
  assert.ok(c.band.peakHz >= 18 && c.band.peakHz <= 32, `peak at ${c.band.peakHz} Hz`);
  assert.ok(c.band.peak > 5 * c.cl95, `peak ${c.band.peak} vs limit ${c.cl95}`);
  // away from the drive (100-400 Hz) coherence stays near chance
  let above = 0;
  let bins = 0;
  for (let k = 0; k < c.f.length; k++)
    if (c.f[k] >= 100 && c.f[k] <= 400) {
      bins++;
      if (c.coh[k] > c.cl95) above++;
    }
  assert.ok(above / bins < 0.12, `${above}/${bins} bins above the limit outside the drive band`);
  // the common part has no delay between the channels
  assert.ok(Math.abs(c.cumulant.peak.lagMs) <= 1, `lag ${c.cumulant.peak.lagMs} ms`);
  assert.ok(c.cumulant.peak.value > 4 * c.cumulant.limit);
  assert.deepEqual(c.warnings, []);
});

test('independent channels stay at chance level', () => {
  const { x, y } = pairWithDrive(60, 0, 11);
  const c = coherence(x, y, FS);
  assert.ok(c.band.above / c.band.bins <= 0.25, `${c.band.above}/${c.band.bins} bins above the limit`);
  assert.ok(c.band.mean < c.cl95, `mean ${c.band.mean} vs ${c.cl95}`);
  assert.ok(Math.abs(c.cumulant.peak.value) < 0.02);
});

test('a delay between the channels shows as the cumulant lag', () => {
  const { x, y } = pairWithDrive(60, 0.6, 5);
  const d = 12; // samples = 6 ms: y follows x
  const yd = Float64Array.from(y, (_, i) => y[Math.max(0, i - d)]);
  const xd = Float64Array.from(x);
  // delay the common modulation of y only: rebuild y from the delayed copy
  const c = coherence(xd, yd, FS);
  assert.ok(Math.abs(c.cumulant.peak.lagMs - 6) <= 1, `lag ${c.cumulant.peak.lagMs} ms`);
});

test('shared mains pickup is flagged and kept out of the band summary', () => {
  const { x, y } = pairWithDrive(40, 0, 3, 60);
  const c = coherence(x, y, FS, { rectify: false });
  assert.ok(c.mainsPeak > 0.5, `mains coherence ${c.mainsPeak}`);
  assert.ok(c.warnings.some((w) => w.includes('50 Hz')));
  assert.ok(c.band.mainsBins >= 1);
  assert.ok(c.band.mean < 3 * c.cl95, `band mean without the mains bins ${c.band.mean}`);
});

test('windows restrict the analysis and lost samples drop their segment', () => {
  // drive only during "swing" (0.6-1.0 s of every 1 s stride)
  const r = rng(21);
  const n = 80 * FS;
  const drive = bandNoise(n, 20, 30, r);
  const v = new Uint16Array(n * 6);
  const strides = [];
  for (let s = 0; s < 80; s++) strides.push({ hs: s, to: s + 0.6, hsNext: s + 1 });
  for (let i = 0; i < n; i++) {
    const ph = (i / FS) % 1;
    const m = ph >= 0.6 ? Math.max(0, 1 + 0.7 * drive[i]) : 1;
    v[i * 6] = Math.round(2048 + 150 * m * gauss(r));
    v[i * 6 + 1] = Math.round(2048 + 150 * m * gauss(r));
  }
  // drop 100 samples in the first swing
  const keep = [];
  for (let i = 0; i < n; i++) if (i < 1400 || i >= 1500) keep.push(i);
  const raw = { n: keep.length, si: Uint32Array.from(keep), v: new Uint16Array(keep.length * 6) };
  keep.forEach((i, j) => raw.v.set(v.subarray(i * 6, i * 6 + 6), j * 6));
  const pair = rawPair(raw, 0, 1);
  assert.equal(pair.missing, 100);
  const meta = { hz: FS, t0: 0 };
  const swing = analyzeRawCoherence(raw, meta, 0, 1, { windows: phaseWindows(strides, 'swing') });
  const stance = analyzeRawCoherence(raw, meta, 0, 1, { windows: phaseWindows(strides, 'stance') });
  assert.equal(swing.windows, 80);
  assert.equal(swing.L, 79); // one 512-sample segment per 0.4 s swing, minus the one with the gap
  assert.equal(swing.skipped, 1);
  assert.equal(stance.L, 160);
  assert.ok(swing.band.peak > 5 * swing.cl95, `swing peak ${swing.band.peak}`);
  assert.ok(stance.band.mean < stance.cl95, `stance mean ${stance.band.mean}`);
  assert.equal(analyzeRawCoherence({ n: 0 }, meta, 0, 1).error, 'This recording has no raw 2 kHz EMG.');
});
