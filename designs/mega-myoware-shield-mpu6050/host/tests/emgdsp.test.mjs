// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/emgdsp.test.mjs   # needs g++
// The ESP32's 2 kHz EMG path (firmware emgdsp.h, compiled natively) against
// simulated MyoWare RAW EMG with a known envelope, compared with the old
// path (one ADC sample per 250 Hz frame, filtered in the app).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { envelope } from '../../web/emg.js';
import { rng } from '../../web/gaitsim.js';

const here = dirname(fileURLToPath(import.meta.url));
const FS = 2000;
const DEC = 8; // 2000 / 250

function build() {
  const exe = join(mkdtempSync(join(tmpdir(), 'emgdsp-')), 'emgdsp_dump');
  execFileSync('g++', ['-std=c++11', '-O2', '-Wall', '-Wextra', '-Werror', '-o', exe, join(here, 'emgdsp_dump.cpp')]);
  return (mode, raw) => execFileSync(exe, { input: `${mode}\n${raw.join('\n')}\n`, encoding: 'utf8' }).trim().split('\n').map(Number);
}

// RAW EMG: 1.65 V offset + a 30-450 Hz random carrier (60 tones) scaled by
// bursts (rest 0.01 V, peaks 0.4 V, 1 s cycle), plus slow motion drift.
function simulate(seconds, seed) {
  const r = rng(seed);
  const tones = Array.from({ length: 60 }, () => ({ f: 30 + 420 * r(), p: 2 * Math.PI * r() }));
  const norm = Math.sqrt(2 / tones.length); // unit RMS carrier
  const amp = (t) => {
    const ph = t % 1;
    return 0.01 + 0.4 * Math.exp(-(((ph - 0.3) / 0.06) ** 2)) + 0.2 * Math.exp(-(((ph - 0.75) / 0.08) ** 2));
  };
  const n = Math.round(seconds * FS);
  const volts = new Float64Array(n);
  const arv = new Float64Array(n); // true ARV of the carrier times the burst: sqrt(2/pi) * rms
  for (let i = 0; i < n; i++) {
    const t = i / FS;
    let c = 0;
    for (const { f, p } of tones) c += Math.sin(2 * Math.PI * f * t + p);
    volts[i] = 1.65 + 0.05 * Math.sin(2 * Math.PI * 1.1 * t) + amp(t) * c * norm;
    arv[i] = amp(t) * Math.sqrt(2 / Math.PI);
  }
  const raw = Array.from(volts, (v) => Math.max(0, Math.min(4095, Math.round((v / 3.3) * 4095))));
  return { raw, arv };
}

const errPct = (est, truth) => {
  let se = 0, st = 0;
  for (let i = 0; i < est.length; i++) { se += (est[i] - truth[i]) ** 2; st += truth[i] ** 2; }
  return 100 * Math.sqrt(se / st);
};

test('2 kHz on-board ARV tracks the true envelope; one sample per frame does not', () => {
  const run = build();
  const { raw, arv } = simulate(12, 4);
  const fs = FS / DEC;
  // Truth on the 250 Hz grid, smoothed like the app smooths the estimates.
  const truth = envelope(Float64Array.from({ length: raw.length / DEC }, (_, k) => arv[k * DEC + DEC / 2]), fs, { signal: 'env', lowpassHz: 6 });

  // New path: firmware ARV, volts = counts * 0.8244 / 1023, then the app's 'arv' envelope.
  const counts = run(1, raw);
  assert.equal(counts.length, raw.length / DEC);
  const onBoard = envelope(Float64Array.from(counts, (c) => (c * 0.8244) / 1023), fs, { signal: 'arv', lowpassHz: 6 });

  // Old path: one ADC sample per frame (counts >> 2, 3.3 V), app's 'raw' envelope.
  const old = envelope(Float64Array.from({ length: counts.length }, (_, k) => ((raw[k * DEC] >> 2) * 3.3) / 1023), fs, { signal: 'raw', lowpassHz: 6 });

  const skip = 2 * fs; // filter start-up
  const cut = (a) => Array.from(a).slice(skip);
  const eNew = errPct(cut(onBoard), cut(truth));
  const eOld = errPct(cut(old), cut(truth));
  console.log(`envelope error: on-board 2 kHz ARV ${eNew.toFixed(1)} %, one sample per frame ${eOld.toFixed(1)} %`);
  assert.ok(eNew < 12, `on-board error ${eNew.toFixed(1)} %`);
  assert.ok(eNew < 0.6 * eOld, `on-board ${eNew.toFixed(1)} % vs old ${eOld.toFixed(1)} %`);

  // Rest level (no burst) close to the true 0.01 V * sqrt(2/pi).
  const restIdx = Array.from({ length: counts.length }, (_, k) => k).filter((k) => k > skip && ((k / fs) % 1 < 0.1 || (k / fs) % 1 > 0.93));
  const rest = restIdx.reduce((s, k) => s + onBoard[k], 0) / restIdx.length;
  assert.ok(Math.abs(rest - 0.008) < 0.004, `rest ${rest.toFixed(4)} V`);
});

test('ENV mode averages the 8 samples to 10-bit counts', () => {
  const run = build();
  const raw = Array.from({ length: 800 }, (_, i) => 2000 + ((i % 8) - 3.5) * 8); // mean 2000 per frame
  const counts = run(0, raw);
  assert.equal(counts.length, 100);
  assert.ok(counts.every((c) => c === 500), counts.slice(0, 5).join(','));
});
