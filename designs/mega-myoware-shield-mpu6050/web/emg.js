// EMG parameters from the MyoWare 2.0 channels, timed by the IMU gait events.
//
// Pipeline (per channel):
//   1. counts -> volts with the board's ADC reference.
//   2. Linear envelope. The shield normally carries the MyoWare ENV output
//      (already rectified and smoothed on the sensor), which is only low-passed
//      again here (zero-phase, 6 Hz). For the RAW output the app removes the
//      offset (20 Hz high-pass), full-wave rectifies and low-passes at 6 Hz.
//      RAW EMG holds energy up to ~450 Hz, so at 250 samples/s it is aliased;
//      use ENV with this recorder.
//   3. Resting baseline: the quietest 0.5 s of the envelope (mean mu, SD sd).
//   4. Activity (on/off): envelope above mu + 3 SD (Hodges & Bui 1996), and at
//      least 10 % of the channel's dynamic range above mu so sensor noise alone
//      cannot switch it on; gaps and bursts shorter than 30 ms are ignored.
//   5. Per stride (heel strike to heel strike from the IMU), the envelope is
//      time-normalised to 0-100 % of the gait cycle and amplitude-normalised
//      to the peak of the channel's mean curve (dynamic peak normalisation; no
//      MVC is recorded). Reported per stride: peak, its timing, mean amplitude
//      in stance, swing and four gait phases, integrated EMG, active % of the
//      cycle and burst on/off times.
//   6. Co-contraction for each pair of channels (Falconer & Winter 1985):
//      CCI = 200 * sum(min(a, b)) / sum(a + b), on the normalised envelopes,
//      over the whole stride and over stance.

import { lowpass, meanSd } from './gait.js';

export const MUSCLES = ['Tibialis anterior', 'Gastrocnemius (medial)', 'Gastrocnemius (lateral)', 'Soleus', 'Peroneus longus', 'Rectus femoris', 'Vastus lateralis', 'Hamstrings', 'Other'];

export const EMG_DEFAULTS = {
  signal: 'env', // 'env' (MyoWare ENV, the default switch position) or 'raw'
  lowpassHz: 6,
  baselineS: 0.5,
  k: 3, // threshold SDs above rest
  minRangeFrac: 0.1,
  minBurstS: 0.03,
};

// Phases of one stride, as fractions of the cycle; TO is the stride's own toe-off.
export const PHASES = [
  ['loading', 'Loading response', (to) => [0, 0.12]],
  ['stance', 'Mid / terminal stance', (to) => [0.12, Math.max(0.12, to - 0.1)]],
  ['pushoff', 'Pre-swing / push-off', (to) => [Math.max(0.12, to - 0.1), to]],
  ['swing', 'Swing', (to) => [to, 1]],
];

export function envelope(volts, fs, o = EMG_DEFAULTS) {
  const fc = Math.min(o.lowpassHz, 0.4 * fs);
  if (o.signal === 'raw') {
    const slow = lowpass(volts, fs, Math.min(20, 0.4 * fs));
    const rect = volts.map((v, i) => Math.abs(v - slow[i]));
    return lowpass(rect, fs, fc);
  }
  return lowpass(volts, fs, fc);
}

function quantile(a, q) {
  const s = Float64Array.from(a).sort();
  return s.length ? s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))] : NaN;
}

// Resting window of the envelope: among the windows with the lowest 20 % of
// means, the steadiest one (smallest SD), so filter ringing next to a burst
// is not taken for rest.
export function baseline(env, fs, o = EMG_DEFAULTS) {
  const w = Math.max(4, Math.round(o.baselineS * fs));
  const wins = [];
  for (let s = 0; s + w <= env.length; s += Math.max(1, w >> 2)) wins.push({ ...meanSd(Array.from(env.subarray(s, s + w))), at: s });
  if (!wins.length) return { mean: NaN, sd: NaN, at: -1 };
  const cut = quantile(wins.map((x) => x.mean), 0.2);
  let best = null;
  for (const x of wins) if (x.mean <= cut && (!best || x.sd < best.sd)) best = x;
  return { mean: best.mean, sd: best.sd, at: best.at };
}

// Boolean activity mask with short gaps and short bursts removed.
export function activity(env, fs, base, o = EMG_DEFAULTS) {
  const top = quantile(env, 0.99);
  const thr = base.mean + Math.max(o.k * base.sd, o.minRangeFrac * (top - base.mean));
  const n = env.length;
  const on = new Uint8Array(n);
  for (let i = 0; i < n; i++) on[i] = env[i] > thr ? 1 : 0;
  const minLen = Math.max(1, Math.round(o.minBurstS * fs));
  const runs = (val, fill) => {
    let i = 0;
    while (i < n) {
      if (on[i] !== val) {
        i++;
        continue;
      }
      let j = i;
      while (j < n && on[j] === val) j++;
      // only interior runs; never flip the edges of the recording
      if (j - i < minLen && i > 0 && j < n) on.fill(fill, i, j);
      i = j;
    }
  };
  runs(0, 1); // close short gaps
  runs(1, 0); // drop short blips
  return { on, threshold: thr };
}

// Linear interpolation of x at fractional index fi.
const at = (x, fi) => {
  const i = Math.floor(fi);
  if (i < 0 || i + 1 >= x.length) return NaN;
  return x[i] + (x[i + 1] - x[i]) * (fi - i);
};

// t: uniform grid (s); channels: [{ch, counts}] on that grid; strides: from the
// gait analysis ({hs, to, hsNext, strideT}).
export function analyzeEmg(t, channels, fs, strides, opts = {}) {
  const o = { ...EMG_DEFAULTS, ...opts };
  const ref = opts.adcRefV || 3.3;
  const P = 101;
  const out = { fs, signal: o.signal, channels: [], cci: [], warnings: [] };
  if (o.signal === 'raw' && fs < 900) out.warnings.push(`RAW EMG needs about 1000 samples per second and this stream has ${fs.toFixed(0)}; it is aliased. Set the MyoWare OUTPUT switch to ENV and the panel's EMG signal to ENV.`);
  const t0 = t[0];
  for (const { ch, counts, muscle } of channels) {
    const volts = Float64Array.from(counts, (c) => (c * ref) / 1023);
    const env = envelope(volts, fs, o);
    const base = baseline(env, fs, o);
    const act = activity(env, fs, base, o);
    const top = quantile(env, 0.99);
    const res = { ch, muscle: muscle || `A${ch}`, env, on: act.on, threshold: act.threshold, baseline: base, strides: [], curve: null, curveNorm: null, summary: {} };
    if (top >= 0.98 * ref) out.warnings.push(`A${ch} reaches the top of the ADC range; lower the MyoWare gain.`);
    if (top - base.mean < 0.02) out.warnings.push(`A${ch} hardly changes (under 20 mV above rest); check the electrodes and cable.`);
    // whole-recording figures (useful without walking too)
    const dur = t[t.length - 1] - t0 || 1;
    let activeN = 0;
    for (let i = 0; i < act.on.length; i++) activeN += act.on[i];
    res.overall = { meanV: meanSd(Array.from(env)).mean, peakV: top, restV: base.mean, restSdV: base.sd, activePct: (100 * activeN) / env.length, durationS: dur };

    // per stride, time-normalised
    const rows = [];
    for (const s of strides) {
      const T = s.strideT;
      const toFrac = (s.to - s.hs) / T;
      const r = new Float64Array(P);
      const a = new Uint8Array(P);
      let ok = true;
      for (let j = 0; j < P; j++) {
        const fi = (s.hs + (j / (P - 1)) * T - t0) * fs;
        r[j] = at(env, fi);
        a[j] = act.on[Math.round(fi)] || 0;
        if (!Number.isFinite(r[j])) ok = false;
      }
      if (!ok) continue;
      rows.push({ s, r, a, toFrac });
    }
    const mean = new Float64Array(P).fill(NaN);
    const sd = new Float64Array(P).fill(NaN);
    for (let j = 0; j < P && rows.length; j++) {
      const m = meanSd(rows.map((x) => x.r[j]));
      mean[j] = m.mean;
      sd[j] = m.sd;
    }
    const norm = rows.length ? Math.max(...mean) - base.mean : NaN; // dynamic peak above rest
    const pct = (v) => (100 * (v - base.mean)) / norm;
    res.normV = norm;
    res.curve = { mean, sd, n: rows.length };
    res.curveNorm = { mean: mean.map(pct), sd: sd.map((v) => (100 * v) / norm), n: rows.length };
    res.rows = rows.map(({ r }) => r.map(pct));
    res.rowTo = rows.map((x) => x.toFrac);

    for (const { s, r, a, toFrac } of rows) {
      let pk = 0;
      for (let j = 1; j < P; j++) if (r[j] > r[pk]) pk = j;
      const span = (f0, f1) => {
        const j0 = Math.round(f0 * (P - 1));
        const j1 = Math.max(j0, Math.round(f1 * (P - 1)));
        let sum = 0;
        for (let j = j0; j <= j1; j++) sum += r[j];
        return sum / (j1 - j0 + 1);
      };
      const integ = (f0, f1) => span(f0, f1) * (f1 - f0) * s.strideT; // V*s
      // bursts in % of cycle
      const bursts = [];
      for (let j = 0; j < P; j++)
        if (a[j] && (j === 0 || !a[j - 1])) {
          let k = j;
          while (k + 1 < P && a[k + 1]) k++;
          bursts.push([j, k]);
          j = k;
        }
      let activeN = 0;
      for (let j = 0; j < P; j++) activeN += a[j];
      const x = {
        peakV: r[pk],
        peakPct: pct(r[pk]),
        peakTiming: pk,
        stanceMean: pct(span(0, toFrac)),
        swingMean: pct(span(toFrac, 1)),
        stanceIemg: integ(0, toFrac) - base.mean * toFrac * s.strideT,
        swingIemg: integ(toFrac, 1) - base.mean * (1 - toFrac) * s.strideT,
        activePct: (100 * activeN) / P,
        bursts: bursts.length,
        onset: bursts.length ? bursts[0][0] : NaN,
        offset: bursts.length ? bursts[0][1] : NaN,
      };
      for (const [key, , win] of PHASES) {
        const [f0, f1] = win(toFrac);
        x[key] = f1 > f0 ? pct(span(f0, f1)) : NaN;
      }
      res.strides.push(x);
    }
    const keys = ['peakV', 'peakPct', 'peakTiming', 'stanceMean', 'swingMean', 'stanceIemg', 'swingIemg', 'activePct', 'bursts', 'onset', 'offset', ...PHASES.map((p) => p[0])];
    for (const k of keys) res.summary[k] = meanSd(res.strides.map((x) => x[k]));
    const pv = res.summary.peakV;
    res.summary.peakCv = pv.n > 1 ? (100 * pv.sd) / pv.mean : NaN;
    out.channels.push(res);
  }

  // Co-contraction for each channel pair (normalised, rest removed, clipped at 0).
  for (let i = 0; i < out.channels.length; i++)
    for (let j = i + 1; j < out.channels.length; j++) {
      const A = out.channels[i];
      const B = out.channels[j];
      const all = [];
      const stance = [];
      const n = Math.min(A.rows.length, B.rows.length);
      for (let k = 0; k < n; k++) {
        const toj = Math.round(A.rowTo[k] * (P - 1));
        const cci = (j0, j1) => {
          let mn = 0;
          let sm = 0;
          for (let q = j0; q <= j1; q++) {
            const a = Math.max(0, A.rows[k][q]);
            const b = Math.max(0, B.rows[k][q]);
            mn += Math.min(a, b);
            sm += a + b;
          }
          return sm > 0 ? (200 * mn) / sm : NaN;
        };
        all.push(cci(0, P - 1));
        stance.push(cci(0, toj));
      }
      out.cci.push({ a: A.ch, b: B.ch, label: `${A.muscle} / ${B.muscle}`, stride: meanSd(all), stance: meanSd(stance) });
    }
  if (!strides.length) out.warnings.push('No strides were found, so the EMG is summarised over the whole stretch only.');
  return out;
}

// Rows for the parameter table: [key, label, note, format digits]
export const EMG_ROWS = [
  ['peakV', 'Peak envelope (V)', 'highest envelope in the stride', 3],
  ['peakTiming', 'Peak timing (% of cycle)', '0 % = heel strike', 0],
  ['onset', 'First burst on (% of cycle)', 'envelope above rest + 3 SD', 0],
  ['offset', 'First burst off (% of cycle)', '', 0],
  ['activePct', 'Active (% of cycle)', 'time above the threshold', 0],
  ['bursts', 'Bursts per stride', '', 1],
  ['loading', 'Loading response (% peak)', '0–12 % of the cycle', 0],
  ['stance', 'Mid / terminal stance (% peak)', '12 % to 10 % before toe-off', 0],
  ['pushoff', 'Pre-swing / push-off (% peak)', 'last 10 % of stance', 0],
  ['swing', 'Swing (% peak)', 'toe-off to next heel strike', 0],
  ['stanceMean', 'Mean in stance (% peak)', '', 0],
  ['swingMean', 'Mean in swing (% peak)', '', 0],
  ['stanceIemg', 'iEMG stance (mV·s)', 'area above rest', 1, 1000],
  ['swingIemg', 'iEMG swing (mV·s)', 'area above rest', 1, 1000],
];
