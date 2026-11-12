// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/emg.test.mjs
// EMG parameters against a simulated walk whose muscle bursts are known
// (web/gaitsim.js emgAt): tibialis anterior around heel strike (3 %) and in
// swing (80 %), gastrocnemius in stance peaking at 45 %.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyzeSource } from '../../web/gait.js';
import { activity, analyzeEmg, baseline, envelope } from '../../web/emg.js';
import { simulateWalk, rng } from '../../web/gaitsim.js';

function source(sim, seed = 9) {
  const r = rng(seed);
  const emg = [0, 1].map((ch) => Float64Array.from(sim.t, (tt) => Math.round(sim.emgAt(tt, ch) * (0.9 + 0.2 * r()) + 8 * (r() - 0.5))));
  return { n: sim.t.length, t: (i) => sim.t[i], v: (k, i) => (k < 6 ? (k < 2 ? emg[k][i] : 0) : sim.imu[Math.floor((k - 6) / 6)][(k - 6) % 6][i]) };
}

for (const fs of [250, 100]) {
  test(`EMG timing, phases and co-contraction at ${fs} Hz`, () => {
    const sim = simulateWalk({ fs, strides: 14, jitter: 0.05, sl: 1.1, seed: 5, limb: 'shank-foot' });
    const res = analyzeSource(source(sim), {
      layout: 'shank-foot',
      emg: { mask: 3, adcRefV: 3.3, muscles: { 0: 'Tibialis anterior', 1: 'Gastrocnemius (medial)' } },
    });
    const e = res.emg;
    assert.equal(e.channels.length, 2);
    assert.deepEqual(e.warnings, []);
    const [ta, ga] = e.channels;
    assert.equal(ta.muscle, 'Tibialis anterior');
    assert.ok(ga.curve.n >= 10, `${ga.curve.n} strides`);
    // resting level: 40 counts = 0.129 V
    assert.ok(Math.abs(ga.baseline.mean - (40 * 3.3) / 1023) < 0.02, `rest ${ga.baseline.mean}`);
    // gastrocnemius peaks at 45 % of the cycle, active in stance only
    assert.ok(Math.abs(ga.summary.peakTiming.mean - 45) < 3, `GA peak at ${ga.summary.peakTiming.mean} %`);
    assert.ok(ga.summary.onset.mean > 20 && ga.summary.onset.mean < 38, `GA on ${ga.summary.onset.mean}`);
    assert.ok(ga.summary.offset.mean > 50 && ga.summary.offset.mean < 66, `GA off ${ga.summary.offset.mean}`);
    assert.ok(ga.summary.stance.mean > 25 && ga.summary.swing.mean < 5 && ga.summary.loading.mean < 5);
    // tibialis anterior: loading response and swing, quiet in mid-stance
    assert.ok(ta.summary.loading.mean > 50 && ta.summary.swing.mean > 25 && ta.summary.stance.mean < 10);
    assert.ok(ta.summary.peakTiming.mean < 8, `TA peak at ${ta.summary.peakTiming.mean} %`);
    assert.ok(ta.summary.stanceIemg.mean > 0 && ga.summary.stanceIemg.mean > ga.summary.swingIemg.mean);
    // the two muscles barely overlap
    assert.equal(e.cci.length, 1);
    assert.ok(e.cci[0].stride.mean < 15, `CCI ${e.cci[0].stride.mean}`);
    assert.equal(ta.curveNorm.mean.length, 101);
    assert.ok(Math.abs(Math.max(...ga.curveNorm.mean) - 100) < 1e-9);
  });
}

test('envelope, baseline and activity on a plain burst; RAW warns when undersampled', () => {
  const fs = 250;
  const n = fs * 6;
  const counts = Float64Array.from({ length: n }, (_, i) => (i > 2 * fs && i < 3 * fs ? 600 : 40));
  const volts = counts.map((c) => (c * 3.3) / 1023);
  const env = envelope(volts, fs);
  const base = baseline(env, fs);
  assert.ok(Math.abs(base.mean - (40 * 3.3) / 1023) < 1e-3);
  const { on } = activity(env, fs, base);
  const active = on.reduce((a, b) => a + b, 0) / fs;
  assert.ok(Math.abs(active - 1) < 0.1, `active ${active} s`);
  const t = Float64Array.from({ length: n }, (_, i) => i / fs);
  const raw = analyzeEmg(t, [{ ch: 0, counts }], fs, [], { signal: 'raw', adcRefV: 3.3 });
  assert.match(raw.warnings.join(' '), /aliased/);
  assert.match(raw.warnings.join(' '), /No strides/);
  assert.ok(raw.channels[0].overall.activePct > 0);
});
