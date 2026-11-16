// Footswitch ground truth for the gait events.
//
// The IMU event rules (gait.js) were written for the shank signal of people
// who land on the heel. In drop foot the contact is often flat or toes-first,
// which is exactly where a shank-gyro rule is least trustworthy, so the event
// times need an independent reference on the same clock. Two force-sensing
// resistors (FSR) under the heel and under the forefoot (first metatarsal
// head or big toe), each wired as a voltage divider into a spare jack of the
// shield, give that reference without a motion-capture lab:
//
//   initial contact (IC) = the first switch of the foot to close,
//   final contact / toe-off (FC) = the last switch to open,
//   contact type = which switch closed first (heel-first, flat, toes-first).
//
// What this is and is not: an FSR closes a few milliseconds after the first
// touch (it needs some force, set by the threshold below) and only sees the
// spot it sits under, so it is a practical reference, not a force plate.
// Report the threshold with any numbers taken from here.
//
// Plain functions on arrays, so they run in the browser and under node.

import { meanSd, median } from './gait.js';

export const FSW_DEFAULTS = {
  thresholdFrac: 0.25, // contact = signal above this fraction of its own range
  hysteresisFrac: 0.05, // of the range, on each side of the threshold
  debounceS: 0.03, // shorter closures and openings are ignored
  minRangeCounts: 40, // a switch that moves less than this never closed
  mergeGapS: 0.05, // heel-off to toe-on gap that still counts as one stance
  flatS: 0.02, // heel and toe within this of each other = flat contact
  tolS: 0.15, // an IMU event further than this from any switch event is unmatched
  maxStanceS: 3, // longer closures are standing, not a stance phase
  invert: false, // true when pressing lowers the voltage (FSR on the ground side)
};

function quantile(x, q) {
  const s = Float64Array.from(x).sort();
  if (!s.length) return NaN;
  return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))];
}

// Contact periods of one switch. t in seconds (ascending), x in ADC counts.
// Returns {ok, periods: [{on, off}], threshold, lo, hi, warning}; on is NaN
// when the switch was already closed at the first sample, off is NaN when it
// was still closed at the last one. Edge times are interpolated to where the
// signal crosses the threshold.
export function switchPeriods(t, x, opts = {}) {
  const o = { ...FSW_DEFAULTS, ...opts };
  const n = Math.min(t.length, x.length);
  const sgn = o.invert ? -1 : 1;
  const v = new Float64Array(n);
  for (let i = 0; i < n; i++) v[i] = sgn * x[i];
  const lo = quantile(v, 0.02);
  const hi = quantile(v, 0.98);
  const range = hi - lo;
  const res = { ok: false, periods: [], threshold: NaN, lo: sgn * lo, hi: sgn * hi, warning: '' };
  if (n < 4 || !(range >= o.minRangeCounts)) {
    res.warning = 'the signal hardly moves, so the switch never closed (or never opened). Check the wiring and that the sensor sits under the foot.';
    return res;
  }
  const thr = lo + o.thresholdFrac * range;
  const h = o.hysteresisFrac * range;
  res.threshold = sgn * thr;
  // state with hysteresis
  const state = new Uint8Array(n);
  let s = v[0] > thr ? 1 : 0;
  for (let i = 0; i < n; i++) {
    if (!s && v[i] > thr + h) s = 1;
    else if (s && v[i] < thr - h) s = 0;
    state[i] = s;
  }
  // debounce: a run shorter than debounceS takes the state around it. Runs
  // touching either end of the record are kept as they are.
  const runs = [];
  for (let i = 0; i < n; ) {
    let j = i;
    while (j < n && state[j] === state[i]) j++;
    runs.push([i, j]);
    i = j;
  }
  for (let pass = 0; pass < 2; pass++) {
    // openings first (a bouncing contact), then closures
    const want = pass === 0 ? 0 : 1;
    for (let k = 1; k + 1 < runs.length; k++) {
      const [a, b] = runs[k];
      if (state[a] === want && t[b] - t[a] < o.debounceS) state.fill(1 - want, a, b);
    }
    runs.length = 0;
    for (let i = 0; i < n; ) {
      let j = i;
      while (j < n && state[j] === state[i]) j++;
      runs.push([i, j]);
      i = j;
    }
  }
  // Time the signal crossed thr going into sample i (state changed at i).
  const crossing = (i, rising) => {
    // walk back to the sample pair that straddles the threshold
    let k = i;
    while (k > 0 && (rising ? v[k - 1] > thr : v[k - 1] < thr)) k--;
    if (k === 0) return t[0];
    const a = v[k - 1];
    const b = v[k];
    const f = b === a ? 1 : (thr - a) / (b - a);
    return t[k - 1] + Math.min(1, Math.max(0, f)) * (t[k] - t[k - 1]);
  };
  for (const [a, b] of runs) {
    if (!state[a]) continue;
    res.periods.push({ on: a === 0 ? NaN : crossing(a, true), off: b === n ? NaN : crossing(b, false) });
  }
  res.ok = res.periods.length > 0;
  if (!res.ok) res.warning = 'no closure found.';
  return res;
}

// Foot contact from a heel and/or a toe switch (either may be null).
// Returns stances: [{ic, fc, type, heelOn, toeOn}] in time order. ic or fc is
// NaN at the ends of the record. type: 'heel' (heel first), 'flat', 'toe'
// (toes first), 'heel-only', 'toe-only'.
export function footContacts(heel, toe, opts = {}) {
  const o = { ...FSW_DEFAULTS, ...opts };
  const all = [];
  for (const [which, sw] of [['heel', heel], ['toe', toe]]) if (sw && sw.ok) for (const p of sw.periods) all.push({ ...p, which });
  const start = (p) => (Number.isFinite(p.on) ? p.on : -Infinity);
  const end = (p) => (Number.isFinite(p.off) ? p.off : Infinity);
  all.sort((a, b) => start(a) - start(b));
  const stances = [];
  for (const p of all) {
    const last = stances[stances.length - 1];
    if (last && start(p) <= last.e + o.mergeGapS) {
      last.e = Math.max(last.e, end(p));
      if (!(p.which in last.first)) last.first[p.which] = start(p);
    } else stances.push({ s: start(p), e: end(p), first: { [p.which]: start(p) } });
  }
  const both = !!(heel && heel.ok && toe && toe.ok);
  return stances.map((st) => {
    const h = st.first.heel;
    const tt = st.first.toe;
    let type;
    if (h === undefined) type = both ? 'toe-only' : 'toe';
    else if (tt === undefined) type = both ? 'heel-only' : 'heel';
    else if (Math.abs(h - tt) <= o.flatS) type = 'flat';
    else type = h < tt ? 'heel' : 'toe';
    const fin = (x) => (Number.isFinite(x) ? x : NaN);
    return { ic: fin(st.s), fc: fin(st.e), type, heelOn: fin(h ?? NaN), toeOn: fin(tt ?? NaN) };
  });
}

export const CONTACT_LABEL = { heel: 'Heel first', flat: 'Flat', toe: 'Toes first', 'heel-only': 'Heel only', 'toe-only': 'Forefoot only' };

// Agreement statistics of paired differences d (seconds, estimate − reference).
export function agreement(d) {
  const v = d.filter(Number.isFinite);
  const m = meanSd(v);
  const abs = v.map(Math.abs);
  return {
    n: v.length,
    bias: m.mean,
    sd: m.sd,
    loa: v.length > 1 ? [m.mean - 1.96 * m.sd, m.mean + 1.96 * m.sd] : [NaN, NaN],
    mae: v.length ? abs.reduce((a, b) => a + b, 0) / v.length : NaN,
    medae: v.length ? median(abs) : NaN,
    maxAbs: v.length ? Math.max(...abs) : NaN,
  };
}

// One-to-one pairing of estimated and reference event times, closest pairs
// first, never further apart than tolS. Returns {pairs: [[iEst, iRef]],
// missed: [iRef] (reference events with no estimate), extra: [iEst]}.
export function matchEvents(est, ref, tolS = FSW_DEFAULTS.tolS) {
  const cand = [];
  for (let i = 0; i < est.length; i++) for (let j = 0; j < ref.length; j++) if (Math.abs(est[i] - ref[j]) <= tolS) cand.push([Math.abs(est[i] - ref[j]), i, j]);
  cand.sort((a, b) => a[0] - b[0]);
  const usedE = new Set();
  const usedR = new Set();
  const pairs = [];
  for (const [, i, j] of cand) {
    if (usedE.has(i) || usedR.has(j)) continue;
    usedE.add(i);
    usedR.add(j);
    pairs.push([i, j]);
  }
  pairs.sort((a, b) => a[0] - b[0]);
  return {
    pairs,
    missed: ref.map((_, j) => j).filter((j) => !usedR.has(j)),
    extra: est.map((_, i) => i).filter((i) => !usedE.has(i)),
  };
}

// Compares one leg's IMU events (the heel strikes and toe-offs of its accepted
// strides) with the footswitch reference.
//   t: time grid; heel, toe: ADC counts on that grid, or null when not fitted.
//   strides: leg.strides from gait.js ({hs, to, hsNext, stanceT, strideT}).
// Reference events outside the walked stretch the IMU analysed (first heel
// strike to last) are left out of the missed count: the IMU analysis only
// claims events inside gait sequences.
export function validateEvents(t, heel, toe, strides, opts = {}) {
  const o = { ...FSW_DEFAULTS, ...opts };
  const out = { ok: false, warnings: [], switches: {}, stances: [], contact: {}, ic: agreement([]), fc: agreement([]), stanceT: agreement([]), strideT: agreement([]), byContact: {}, missed: { ic: 0, fc: 0 }, extra: { ic: 0, fc: 0 }, rows: [], opts: { thresholdFrac: o.thresholdFrac, tolS: o.tolS } };
  const sw = {};
  for (const [name, x] of [['heel', heel], ['toe', toe]]) {
    if (!x) continue;
    sw[name] = switchPeriods(t, x, o);
    out.switches[name] = { ok: sw[name].ok, threshold: sw[name].threshold, lo: sw[name].lo, hi: sw[name].hi, closures: sw[name].periods.length };
    if (!sw[name].ok) out.warnings.push(`${name === 'heel' ? 'Heel' : 'Forefoot'} switch: ${sw[name].warning}`);
  }
  const hasHeel = !!(sw.heel && sw.heel.ok);
  const hasToe = !!(sw.toe && sw.toe.ok);
  if (!hasHeel && !hasToe) return out;
  if (!hasToe) out.warnings.push('Only a heel switch: toe-off has no reference (the heel lifts well before the toes leave), and a toes-first contact is seen late. Add a forefoot switch.');
  if (!hasHeel) out.warnings.push('Only a forefoot switch: initial contact has a reference only when the forefoot lands first. Add a heel switch.');
  out.stances = footContacts(sw.heel, sw.toe, o);
  for (const s of out.stances) if (Number.isFinite(s.ic)) out.contact[s.type] = (out.contact[s.type] || 0) + 1;
  if (!strides || !strides.length) {
    out.warnings.push('No strides from the IMU in this stretch, so there is nothing to compare.');
    return out;
  }

  // IMU events: each heel strike and toe-off once.
  const estIc = [...new Set(strides.flatMap((s) => [s.hs, s.hsNext]))].sort((a, b) => a - b);
  const estFc = [...new Set(strides.map((s) => s.to))].sort((a, b) => a - b);
  const span = [estIc[0] - o.tolS, estIc[estIc.length - 1] + o.tolS];
  const inSpan = (x) => x >= span[0] && x <= span[1];
  const useIc = hasHeel || hasToe; // with a forefoot switch alone, IC is only fair for toes-first; flagged above
  const refIcSt = out.stances.filter((s) => Number.isFinite(s.ic) && inSpan(s.ic));
  const refFcSt = hasToe ? out.stances.filter((s) => Number.isFinite(s.fc) && inSpan(s.fc)) : [];
  const refIc = useIc ? refIcSt.map((s) => s.ic) : [];
  const refFc = refFcSt.map((s) => s.fc);
  const mIc = matchEvents(estIc, refIc, o.tolS);
  const mFc = matchEvents(estFc, refFc, o.tolS);
  const icRef = new Map(mIc.pairs.map(([i, j]) => [estIc[i], refIcSt[j]]));
  const fcRef = new Map(mFc.pairs.map(([i, j]) => [estFc[i], refFcSt[j]]));
  out.ic = agreement(mIc.pairs.map(([i, j]) => estIc[i] - refIc[j]));
  out.fc = agreement(mFc.pairs.map(([i, j]) => estFc[i] - refFc[j]));
  out.missed = { ic: mIc.missed.length, fc: mFc.missed.length };
  out.extra = { ic: mIc.extra.length, fc: mFc.extra.length };
  const groups = {};
  for (const [i, j] of mIc.pairs) (groups[refIcSt[j].type] ||= []).push(estIc[i] - refIc[j]);
  for (const [k, d] of Object.entries(groups)) out.byContact[k] = agreement(d);

  const dStance = [];
  const dStride = [];
  strides.forEach((s, k) => {
    const a = icRef.get(s.hs);
    const b = fcRef.get(s.to);
    const c = icRef.get(s.hsNext);
    const row = {
      stride: k + 1,
      hs: s.hs,
      refHs: a ? a.ic : NaN,
      to: s.to,
      refTo: b ? b.fc : NaN,
      hsNext: s.hsNext,
      refHsNext: c ? c.ic : NaN,
      contact: a ? a.type : '',
      stanceT: s.stanceT,
      refStanceT: a && b && b.fc > a.ic ? b.fc - a.ic : NaN,
      strideT: s.strideT,
      refStrideT: a && c ? c.ic - a.ic : NaN,
    };
    if (Number.isFinite(row.refStanceT)) dStance.push(row.stanceT - row.refStanceT);
    if (Number.isFinite(row.refStrideT)) dStride.push(row.strideT - row.refStrideT);
    out.rows.push(row);
  });
  out.stanceT = agreement(dStance);
  out.strideT = agreement(dStride);
  out.ok = out.ic.n + out.fc.n > 0;
  if (!out.ok) out.warnings.push(`No IMU event within ${Math.round(o.tolS * 1000)} ms of a switch event. Check that the switches are on the same leg as the sensors.`);
  return out;
}

// One row per stride, for CSV export. Times in seconds, differences in ms
// (IMU − footswitch: positive = the IMU event is late).
export function footswitchCsv(v, name = '') {
  const f3 = (x) => (Number.isFinite(x) ? x.toFixed(3) : '');
  const ms = (a, b) => (Number.isFinite(a) && Number.isFinite(b) ? ((a - b) * 1000).toFixed(1) : '');
  const head = ['stride', 'contact', 'imu_hs_s', 'fsw_ic_s', 'hs_diff_ms', 'imu_to_s', 'fsw_fc_s', 'to_diff_ms', 'imu_stance_s', 'fsw_stance_s', 'stance_diff_ms', 'imu_stride_s', 'fsw_stride_s', 'stride_diff_ms'];
  const lines = [
    `# IMU gait events against footswitches${name ? ` for ${name}` : ''}; differences are IMU − footswitch in ms (positive = IMU late); switch threshold ${Math.round(v.opts.thresholdFrac * 100)} % of each switch's range; events paired within ${Math.round(v.opts.tolS * 1000)} ms; IC = first switch to close, FC = last to open`,
    head.join(','),
  ];
  for (const r of v.rows)
    lines.push([r.stride, r.contact, f3(r.hs), f3(r.refHs), ms(r.hs, r.refHs), f3(r.to), f3(r.refTo), ms(r.to, r.refTo), f3(r.stanceT), f3(r.refStanceT), ms(r.stanceT, r.refStanceT), f3(r.strideT), f3(r.refStrideT), ms(r.strideT, r.refStrideT)].join(','));
  return lines.join('\n') + '\n';
}
