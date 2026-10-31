// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/hmm.test.mjs
// The JavaScript port of gaitmap's pre-trained stride HMM (web/hmm.js) must
// give the same answer as gaitmap itself. fixtures/gaitmap-hmm-reference.json
// holds gaitmap 2.6.0's own output on two simulated shank recordings.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { segment, butterLowpassSos, fftResample, MODEL } from '../../web/hmm.js';
import { analyzeLeg } from '../../web/gait.js';
import { simulateWalk } from '../../web/gaitsim.js';

const ref = JSON.parse(fs.readFileSync(new URL('./fixtures/gaitmap-hmm-reference.json', import.meta.url)));

test('model loads with the published structure', () => {
  assert.equal(MODEL.states.length, 25);
  assert.equal(MODEL.transitionStates, 5);
  assert.equal(MODEL.strideStates, 20);
  assert.equal(MODEL.featureSpaceHz, 51.2);
  for (const row of MODEL.trans) assert.ok(Math.abs(row.reduce((a, b) => a + b, 0) - 1) < 1e-9);
  assert.ok(Math.abs(MODEL.start.reduce((a, b) => a + b, 0) - 1) < 1e-9);
});

for (const c of ref.cases)
  test(`same strides and states as gaitmap: ${c.name}`, () => {
    const r = segment(Float64Array.from(c.gyrMl), c.fs);
    assert.deepEqual(r.strides, c.strides);
    const states = [];
    for (const [s, k] of c.statesRle) for (let i = 0; i < k; i++) states.push(s);
    assert.deepEqual(Array.from(r.states), states);
  });

test('filter and resampling match scipy', () => {
  // scipy.signal.butter(4, 10, fs=204.8, output='sos')
  const sos = butterLowpassSos(4, 10, 204.8);
  assert.ok(Math.abs(sos[0][0] - 3.820209607982637e-4) < 1e-15);
  assert.ok(Math.abs(sos[1][4] + 1.7090881897476977) < 1e-12);
  // resampling a pure tone keeps it (odd length, Bluestein path)
  const n = 1001, m = 251;
  const x = Float64Array.from({ length: n }, (_, i) => Math.sin((2 * Math.PI * 7 * i) / n));
  const y = fftResample(x, m);
  for (let i = 0; i < m; i++) assert.ok(Math.abs(y[i] - Math.sin((2 * Math.PI * 7 * i) / m)) < 1e-9);
});

test('as the app stride finder: every simulated stride, same timing as the peak rules', () => {
  for (const fs of [60, 100, 245]) {
    const sim = simulateWalk({ fs, strides: 12, jitter: 0.06, seed: fs + 1 });
    const leg = analyzeLeg(sim.t, sim.imu[0].slice(0, 3), sim.imu[0].slice(3, 6), fs, { segmenter: 'hmm' });
    assert.equal(leg.segmenter, 'hmm');
    assert.ok(leg.strides.length >= sim.truth[0].ic.length - 2, `${fs} Hz: ${leg.strides.length}`);
    const peaks = analyzeLeg(sim.t, sim.imu[0].slice(0, 3), sim.imu[0].slice(3, 6), fs);
    assert.deepEqual(leg.strides.map((s) => s.hs), peaks.strides.map((s) => s.hs));
  }
});

test('below 51.2 samples per second it falls back to the peak rules', () => {
  const sim = simulateWalk({ fs: 29, strides: 8, seed: 3 });
  const leg = analyzeLeg(sim.t, sim.imu[0].slice(0, 3), sim.imu[0].slice(3, 6), 29, { segmenter: 'hmm' });
  assert.equal(leg.segmenter, 'peaks');
  assert.match(leg.warnings.join(' '), /51\.2/);
  assert.ok(leg.strides.length >= 6);
});
