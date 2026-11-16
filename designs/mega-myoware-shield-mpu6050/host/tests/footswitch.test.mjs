// Run: node --test designs/mega-myoware-shield-mpu6050/host/tests/footswitch.test.mjs
// Footswitch reference for the gait events (web/footswitch.js): switch edges,
// contact type, event pairing and the agreement numbers, on hand-made signals
// and on the simulated walk, whose switches are offset from the IMU events by
// known amounts. This proves the arithmetic, not how a real FSR behaves.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { switchPeriods, footContacts, matchEvents, agreement, validateEvents, footswitchCsv } from '../../web/footswitch.js';
import { analyzeShankFoot, analyzeSource } from '../../web/gait.js';
import { simulateWalk } from '../../web/gaitsim.js';

const grid = (n, fs) => Float64Array.from({ length: n }, (_, i) => i / fs);
// trapezoid pulses: [on, off] times, 10 ms linear edges centred on those times
function pulses(t, list, { lo = 60, hi = 860, edge = 0.01 } = {}) {
  return Float64Array.from(t, (tt) => {
    let v = 0;
    for (const [a, b] of list) v = Math.max(v, Math.min(1, Math.max(0, (tt - a) / edge + 0.5), Math.max(0, (b - tt) / edge + 0.5)));
    return lo + (hi - lo) * v;
  });
}

test('switch edges are timed to the threshold crossing, between samples', () => {
  const t = grid(1000, 250);
  const x = pulses(t, [[1.0, 1.6], [2.2, 2.8]]);
  const r = switchPeriods(t, x);
  assert.equal(r.ok, true);
  assert.equal(r.periods.length, 2);
  // threshold at 25 % of the range: 2.5 ms before the centre of a rising edge, 2.5 ms after on a falling one
  assert.ok(Math.abs(r.periods[0].on - 0.9975) < 0.0006, `on ${r.periods[0].on}`);
  assert.ok(Math.abs(r.periods[0].off - 1.6025) < 0.0006, `off ${r.periods[0].off}`);
  assert.ok(Math.abs(r.threshold - 260) < 2);
});

test('bounce and glitches are ignored; an inverted switch reads the same', () => {
  const t = grid(1000, 250);
  const x = pulses(t, [[1.0, 1.6]]);
  for (let i = 0; i < t.length; i++) {
    if (t[i] > 1.2 && t[i] < 1.212) x[i] = 60; // 12 ms opening while loaded
    if (t[i] > 3.0 && t[i] < 3.012) x[i] = 860; // 12 ms spike in swing
  }
  const r = switchPeriods(t, x);
  assert.equal(r.periods.length, 1);
  assert.ok(Math.abs(r.periods[0].off - r.periods[0].on - 0.605) < 0.002);
  const inv = switchPeriods(t, x.map((v) => 920 - v), { invert: true });
  assert.equal(inv.periods.length, 1);
  assert.ok(Math.abs(inv.periods[0].on - r.periods[0].on) < 1e-9);
});

test('a flat signal and a switch closed at both ends are reported honestly', () => {
  const t = grid(500, 250);
  const flat = switchPeriods(t, Float64Array.from(t, (_, i) => 500 + (i % 3)));
  assert.equal(flat.ok, false);
  assert.match(flat.warning, /hardly moves/);
  const x = pulses(t, [[-1, 0.5], [1.5, 9]]);
  const r = switchPeriods(t, x);
  assert.equal(r.periods.length, 2);
  assert.ok(Number.isNaN(r.periods[0].on) && Number.isFinite(r.periods[0].off));
  assert.ok(Number.isFinite(r.periods[1].on) && Number.isNaN(r.periods[1].off));
});

test('contact type from the order the switches close', () => {
  const t = grid(2500, 250);
  // stance 1: heel 80 ms before toe; stance 2: together; stance 3: toe 100 ms first; stance 4: toe only
  const heel = switchPeriods(t, pulses(t, [[1.0, 1.4], [3.0, 3.4], [5.1, 5.4]]));
  const toe = switchPeriods(t, pulses(t, [[1.08, 1.65], [3.005, 3.65], [5.0, 5.65], [7.0, 7.6]]));
  const st = footContacts(heel, toe);
  assert.deepEqual(st.map((s) => s.type), ['heel', 'flat', 'toe', 'toe-only']);
  assert.ok(Math.abs(st[0].ic - 0.9975) < 0.001 && Math.abs(st[0].fc - 1.6525) < 0.001);
  assert.ok(Math.abs(st[2].ic - 4.9975) < 0.001);
  // one switch alone
  assert.deepEqual(footContacts(heel, null).map((s) => s.type), ['heel', 'heel', 'heel']);
});

test('pairing is one-to-one and counts missed and extra events', () => {
  const m = matchEvents([1.02, 2.0, 2.05, 5.0], [1.0, 2.04, 3.0], 0.15);
  assert.deepEqual(m.pairs, [[0, 0], [2, 1]]);
  assert.deepEqual(m.missed, [2]);
  assert.deepEqual(m.extra, [1, 3]);
  const a = agreement([0.01, 0.03, -0.01, 0.01]);
  assert.ok(Math.abs(a.bias - 0.01) < 1e-12 && Math.abs(a.mae - 0.015) < 1e-12 && Math.abs(a.medae - 0.01) < 1e-12);
  assert.ok(Math.abs(a.loa[1] - a.loa[0] - 2 * 1.96 * a.sd) < 1e-12);
});

for (const contact of ['heel', 'toe']) {
  test(`simulated walk, ${contact}-first contact: recovers the known switch offsets`, () => {
    const fs = 250;
    const sim = simulateWalk({ fs, strides: 16, jitter: 0.05, seed: 5, limb: 'shank-foot' });
    const leg = analyzeShankFoot(sim.t, { acc: sim.imu[0].slice(0, 3), gyr: sim.imu[0].slice(3, 6) }, { acc: sim.imu[1].slice(0, 3), gyr: sim.imu[1].slice(3, 6) }, fs);
    assert.ok(leg.strides.length >= 13);
    const sig = (which) => Float64Array.from(sim.t, (tt, i) => 60 + 800 * sim.switchAt(tt, which, contact) + 6 * Math.sin(i * 1.7));
    const v = validateEvents(sim.t, sig('heel'), sig('toe'), leg.strides);
    assert.equal(v.ok, true, v.warnings.join(' '));
    // the switch closes 15 ms before the IMU's heel strike and opens 25 ms after its toe-off
    assert.equal(v.ic.n, leg.strides.length + 1);
    assert.equal(v.fc.n, leg.strides.length);
    assert.ok(Math.abs(v.ic.bias * 1000 - 15) < 6, `IC bias ${v.ic.bias * 1000} ms`);
    assert.ok(Math.abs(v.fc.bias * 1000 + 25) < 6, `FC bias ${v.fc.bias * 1000} ms`);
    assert.ok(v.ic.sd * 1000 < 5 && v.fc.sd * 1000 < 5);
    assert.deepEqual(v.missed, { ic: 0, fc: 0 });
    assert.deepEqual(v.extra, { ic: 0, fc: 0 });
    // stance by the switches is about 40 ms longer than by the IMU: the two event offsets added up
    assert.ok(Math.abs(v.stanceT.bias - (v.fc.bias - v.ic.bias)) * 1000 < 2, `stance bias ${v.stanceT.bias * 1000}`);
    assert.ok(Math.abs(v.stanceT.bias * 1000 + 40) < 12);
    assert.ok(Math.abs(v.strideT.bias) * 1000 < 3);
    assert.deepEqual(Object.keys(v.byContact), [contact]);
    assert.equal(v.byContact[contact].n, v.ic.n);
    const csv = footswitchCsv(v, 'walk');
    assert.equal(csv.trim().split('\n').length, 2 + leg.strides.length);
    assert.match(csv.split('\n')[2], new RegExp(`^1,${contact},`));
  });
}

test('one switch only: the comparison is limited and says why', () => {
  const fs = 250;
  const sim = simulateWalk({ fs, strides: 10, seed: 9, limb: 'shank-foot' });
  const leg = analyzeShankFoot(sim.t, { acc: sim.imu[0].slice(0, 3), gyr: sim.imu[0].slice(3, 6) }, { acc: sim.imu[1].slice(0, 3), gyr: sim.imu[1].slice(3, 6) }, fs);
  const heel = Float64Array.from(sim.t, (tt) => 60 + 800 * sim.switchAt(tt, 'heel'));
  const v = validateEvents(sim.t, heel, null, leg.strides);
  assert.ok(v.ic.n >= leg.strides.length);
  assert.equal(v.fc.n, 0);
  assert.ok(v.warnings.some((w) => /Only a heel switch/.test(w)));
  const none = validateEvents(sim.t, Float64Array.from(sim.t, () => 300), null, leg.strides);
  assert.equal(none.ok, false);
  assert.ok(none.warnings.some((w) => /hardly moves/.test(w)));
});

test('analyzeSource: switch jacks are compared with the events and kept out of the EMG', () => {
  const fs = 250;
  const sim = simulateWalk({ fs, strides: 12, seed: 4, limb: 'shank-foot' });
  const src = {
    n: sim.t.length,
    t: (i) => sim.t[i],
    v: (key, i) => {
      if (key === 0) return sim.emgAt(sim.t[i], 0);
      if (key === 4) return 60 + 800 * sim.switchAt(sim.t[i], 'heel');
      if (key === 5) return 60 + 800 * sim.switchAt(sim.t[i], 'toe');
      if (key < 6) return 0;
      return sim.imu[key < 12 ? 0 : 1][(key - 6) % 6][i];
    },
  };
  const r = analyzeSource(src, { layout: 'shank-foot', limb: { shank: 'A', side: 'right' }, emg: { mask: 0b110001, adcRefV: 3.3 }, switches: { heel: 4, toe: 5 } });
  assert.deepEqual(r.emg.channels.map((c) => c.ch), [0]);
  assert.equal(r.footswitch.leg, 'right');
  assert.equal(r.footswitch.ok, true);
  assert.ok(Math.abs(r.footswitch.ic.bias * 1000 - 15) < 6);
  // a jack that is not enabled gives a clear note instead of a result
  const off = analyzeSource(src, { layout: 'shank-foot', emg: { mask: 0b000001, adcRefV: 3.3 }, switches: { heel: 4, toe: -1 } });
  assert.equal(off.footswitch.ok, false);
  assert.match(off.footswitch.warnings[0], /A4 is not enabled/);
  // no switches chosen: nothing added
  assert.equal(analyzeSource(src, { layout: 'shank-foot', emg: { mask: 1, adcRefV: 3.3 } }).footswitch, undefined);
});
