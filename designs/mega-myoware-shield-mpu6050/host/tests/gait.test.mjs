// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/gait.test.mjs
// Checks the gait analysis against synthetic shank signals with known heel
// strikes, toe-offs and stride length (web/gaitsim.js), at the stream rates
// the board can reach: 29 Hz (ZS-040 at 9600 baud), 100 Hz (the papers) and
// 245 Hz (115200 baud). The simulation is a model, so this proves the code
// does what it says, not that a real shank looks exactly like this.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { analyzeLeg, analyzeSource, combine, lowpass, resample, stridesCsv, strideFromWalk } from '../../web/gait.js';
import { simulateWalk } from '../../web/gaitsim.js';

const nearest = (list, x) => Math.min(...list.map((v) => Math.abs(v - x)));

for (const [fs, tolMs, tolPct] of [
  [245, 8, 1.5],
  [100, 10, 1.5],
  [29, 20, 3],
]) {
  test(`events, timing and stride length at ${fs} Hz`, () => {
    const sim = simulateWalk({ fs, strides: 14, jitter: 0.06, sl: 1.15, seed: fs });
    const legs = {};
    for (const k of [0, 1]) {
      const leg = analyzeLeg(sim.t, sim.imu[k].slice(0, 3), sim.imu[k].slice(3, 6), fs);
      legs[k ? 'left' : 'right'] = leg;
      const truth = sim.truth[k];
      // every complete stride between the first and last true heel strike
      assert.ok(leg.strides.length >= truth.ic.length - 2, `leg ${k}: ${leg.strides.length} strides for ${truth.ic.length} heel strikes`);
      for (const s of leg.strides) {
        assert.ok(nearest(truth.ic, s.hs) * 1000 < tolMs, `HS ${s.hs}`);
        assert.ok(nearest(truth.to, s.to) * 1000 < tolMs, `TO ${s.to}`);
        // stance % against the true events of this stride
        const hs = truth.ic.reduce((a, b) => (Math.abs(b - s.hs) < Math.abs(a - s.hs) ? b : a));
        const to = truth.to.reduce((a, b) => (Math.abs(b - s.to) < Math.abs(a - s.to) ? b : a));
        const next = truth.ic.reduce((a, b) => (Math.abs(b - s.hsNext) < Math.abs(a - s.hsNext) ? b : a));
        const truePct = (100 * (to - hs)) / (next - hs);
        assert.ok(Math.abs(s.stancePct - truePct) < tolPct, `stance ${s.stancePct} vs ${truePct}`);
      }
      const lengths = leg.strides.map((s) => s.length).filter(Number.isFinite);
      assert.ok(lengths.length >= leg.strides.length - 1);
      for (const l of lengths) assert.ok(Math.abs(l - sim.sl) / sim.sl < 0.05, `stride length ${l}`);
      assert.match(leg.bias, /still window/);
    }
    const c = combine(legs, 10);
    const meanT = sim.durs.reduce((a, b) => a + b, 0) / sim.durs.length;
    assert.ok(Math.abs(c.cadenceSteps - 120 / meanT) < 3, `cadence ${c.cadenceSteps}`);
    assert.ok(Math.abs(c.stepT.mean - meanT / 2) < 0.03, `step ${c.stepT.mean}`);
    // stance 61.5 % each side -> double support about 2 × 11.5 %
    assert.ok(Math.abs(c.doubleSupportPct.mean - 2 * (sim.stancePct - 50)) < 3, `double support ${c.doubleSupportPct.mean}`);
    // Eq. 4: distance ÷ number of strides; gait speed = distance ÷ time
    assert.ok(Math.abs(c.meanStrideLength - 10 / (c.walkTimeS / c.strideT.mean)) < 1e-9);
    assert.ok(Math.abs(c.gaitSpeed - 10 / c.walkTimeS) < 1e-9);
    assert.ok(c.symmetry.stanceT < 3);
  });
}

test('no strides from standing, swaying or noise', () => {
  const fs = 100;
  const n = fs * 60;
  const t = Float64Array.from({ length: n }, (_, i) => i / fs);
  const col = (f) => [0, 1, 2].map((a) => Float64Array.from({ length: n }, (_, i) => f(i, a)));
  let r = 0.5;
  const rnd = () => ((r = (r * 9301 + 49297) % 233280) / 233280) - 0.5;
  const still = analyzeLeg(t, col((i, a) => (a === 2 ? 1 : 0) + 0.01 * rnd()), col(() => 0.5 * rnd()), fs);
  assert.equal(still.strides.length, 0);
  const sway = analyzeLeg(t, col((i, a) => (a === 2 ? 1 : 0.05 * Math.sin(i / 40))), col((i, a) => 35 * Math.sin((2 * Math.PI * 0.15 * i) / fs + a) + 25 * rnd()), fs);
  assert.equal(sway.strides.length, 0);
});

test('lost samples and failed IMU reads are bridged', () => {
  const sim = simulateWalk({ fs: 100, strides: 10, seed: 5 });
  // drop 3 % of samples and blank a few reads, as the Bluetooth link might
  const keep = [];
  for (let i = 0; i < sim.t.length; i++) if ((i * 7919) % 100 >= 3) keep.push(i);
  const t = keep.map((i) => sim.t[i]);
  const src = {
    n: keep.length,
    t: (i) => t[i],
    v: (key, i) => {
      const k = key < 12 ? 0 : 1;
      if (i % 211 === 0) return NaN;
      return sim.imu[k][(key - 6) % 6][keep[i]];
    },
  };
  const res = analyzeSource(src, { imuMask: 3, sides: { A: 'right', B: 'left' }, distanceM: 10 });
  assert.ok(res.legs.right.strides.length >= 8, `right ${res.legs.right.strides.length}`);
  assert.ok(res.legs.left.strides.length >= 8, `left ${res.legs.left.strides.length}`);
  assert.ok(res.combined.gaitSpeed > 0);
  const csv = stridesCsv(res, 'x').trim().split('\n');
  assert.equal(csv[1].split(',')[0], 'leg');
  assert.equal(csv.length - 2, res.combined.strides);
});

test('one IMU only, and an IMU marked as not on a leg', () => {
  const sim = simulateWalk({ fs: 100, strides: 10, seed: 9 });
  const src = { n: sim.t.length, t: (i) => sim.t[i], v: (key, i) => sim.imu[key < 12 ? 0 : 1][(key - 6) % 6][i] };
  const one = analyzeSource(src, { imuMask: 1, sides: { A: 'left', B: 'right' } });
  assert.deepEqual(Object.keys(one.legs), ['left']);
  assert.ok(Number.isNaN(one.combined.doubleSupportPct.mean));
  assert.ok(one.combined.cadenceSteps > 100);
  const off = analyzeSource(src, { imuMask: 3, sides: { A: 'off', B: 'right' } });
  assert.deepEqual(Object.keys(off.legs), ['right']);
  assert.ok(off.warnings.length === 0);
});

test('low rate warning and helpers', () => {
  const sim = simulateWalk({ fs: 29, strides: 6, seed: 2 });
  const src = { n: sim.t.length, t: (i) => sim.t[i], v: (key, i) => sim.imu[key < 12 ? 0 : 1][(key - 6) % 6][i] };
  assert.match(analyzeSource(src).warnings.join(' '), /115200/);
  const y = lowpass(Float64Array.from({ length: 200 }, () => 3), 100, 5);
  assert.ok(Math.abs(y[100] - 3) < 1e-9);
  const r = resample(Float64Array.from([0, 0.01, 0.03]), [Float64Array.from([0, 1, 3])], 100);
  assert.deepEqual(Array.from(r.channels[0]).map((v) => +v.toFixed(6)), [0, 1, 2, 3]);
});

test('strides with a clipped accelerometer get no sensor length', () => {
  const sim = simulateWalk({ fs: 100, strides: 8, seed: 4 });
  const acc = sim.imu[0].slice(0, 3).map((x) => x.map((v) => Math.max(-2, Math.min(2, v)))); // as if the range were ±2 g
  const leg = analyzeLeg(sim.t, acc, sim.imu[0].slice(3, 6), 100, { accelRangeG: 2 });
  assert.ok(leg.strides.length >= 6);
  assert.ok(leg.strides.every((s) => Number.isNaN(s.length)));
  assert.match(leg.warnings.join(' '), /±2 g limit/);
});

test('a person’s measured stride length sets length and speed, and scales the sensor estimate', () => {
  const sim = simulateWalk({ fs: 100, strides: 10, sl: 1.15, seed: 12 });
  const src = { n: sim.t.length, t: (i) => sim.t[i], v: (key, i) => sim.imu[key < 12 ? 0 : 1][(key - 6) % 6][i] };
  assert.equal(strideFromWalk(10, 16), 1.25);
  assert.ok(Number.isNaN(strideFromWalk(10, 0)));
  const plain = analyzeSource(src).combined;
  assert.equal(plain.strideLength.source, 'sensor');
  const p = analyzeSource(src, { personStrideM: 0.9 }).combined;
  assert.equal(p.strideLength.source, 'person');
  assert.equal(p.strideLength.value, 0.9);
  assert.ok(Math.abs(p.speed.value - 0.9 / p.strideT.mean) < 1e-12);
  assert.ok(Math.abs(p.personLength.mean - 0.9) < 1e-9, 'scaled lengths average to the measured stride');
  assert.ok(p.personLength.sd > 0, 'stride-to-stride variation kept');
  // a walk distance (Eq. 4) still wins
  const e = analyzeSource(src, { personStrideM: 0.9, distanceM: 10 }).combined;
  assert.equal(e.strideLength.source, 'eq4');
  const csv = stridesCsv(analyzeSource(src, { personStrideM: 0.9 }), 'p').trim().split('\n');
  assert.ok(csv[1].endsWith('stride_length_person_m,stride_speed_person_m_s'));
});
