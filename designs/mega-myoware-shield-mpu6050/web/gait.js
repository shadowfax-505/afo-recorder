// Gait analysis from shank-mounted MPU-6050s (one per leg, just above the
// lateral malleolus), following the pipeline in the reference papers:
//
//   Quiguanas-López et al., Results in Engineering 29 (2026) 109173
//     preprocessing: gyro bias from a resting window, PCA axis alignment,
//     forward-direction (sign) correction; gait sequences located first, then
//     strides; spatio-temporal parameters by their Eqs. 1–4.
//   Carcreff et al., Sensors 18 (2018) 394, "Shanks" configuration
//     (Salarian et al.): gait events by peak detection on the shank's pitch
//     (sagittal) angular velocity: mid-swing = large positive peak, initial
//     contact = the minimum after it, toe-off = the minimum before it.
//   Mariani et al. (the "Feet" configuration in Carcreff): stride length by
//     de-drifted double integration of gravity-free acceleration between two
//     zero-velocity instants. Used here with the sensor at ankle level, whose
//     velocity is close to zero at mid-stance.
//
// The gaitmap steps the first paper names (UllrichGaitSequenceDetection,
// the pre-trained stride HMM, HerzerEventDetection) are reproduced in spirit,
// not byte for byte: the HMM's trained weights are not published in the paper,
// so strides are segmented from the detected events instead.
//
// Everything here is plain functions on arrays so it runs in the browser and
// under node for tests.

const G = 9.80665;
const RAD = Math.PI / 180;

export const DEFAULTS = {
  restWindowS: 1.0, // still window used for gyro bias
  restGyroSd: 3, // °/s, max per-axis SD to call a window still
  seqWindowS: 4, // gait sequence detection window
  seqStepS: 1,
  seqMinSd: 25, // °/s, sagittal gyro SD needed to call a window walking
  seqBand: [0.35, 2.5], // stride frequency band, Hz
  seqMinProminence: 4, // dominant peak power over mean power in 0.1–6 Hz
  msMinDps: 50, // mid-swing peak must exceed this
  strideTRange: [0.45, 3.0], // s
  stancePctRange: [30, 85], // %
  accelRangeG: 8, // full scale; strides with clipped acceleration get no length
};

// ---------- small numeric helpers ----------

export function median(a) {
  if (!a.length) return NaN;
  const s = Float64Array.from(a).sort();
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function meanSd(a) {
  const v = a.filter((x) => Number.isFinite(x));
  if (!v.length) return { mean: NaN, sd: NaN, n: 0 };
  const mean = v.reduce((s, x) => s + x, 0) / v.length;
  const sd = v.length > 1 ? Math.sqrt(v.reduce((s, x) => s + (x - mean) ** 2, 0) / (v.length - 1)) : 0;
  return { mean, sd, n: v.length };
}

function quantile(arr, q) {
  const s = Float64Array.from(arr).sort();
  if (!s.length) return NaN;
  const i = Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))));
  return s[i];
}

// 2nd-order Butterworth low-pass, run forward and backward (zero phase).
export function lowpass(x, fs, fc) {
  if (!(fc > 0) || fc >= fs / 2 || x.length < 4) return Float64Array.from(x);
  const k = Math.tan((Math.PI * fc) / fs);
  const q = Math.SQRT1_2;
  const norm = 1 / (1 + k / q + k * k);
  const b0 = k * k * norm;
  const b1 = 2 * b0;
  const b2 = b0;
  const a1 = 2 * (k * k - 1) * norm;
  const a2 = (1 - k / q + k * k) * norm;
  const run = (src) => {
    const y = new Float64Array(src.length);
    let x1 = src[0];
    let x2 = src[0];
    let y1 = src[0];
    let y2 = src[0];
    for (let i = 0; i < src.length; i++) {
      const v = b0 * src[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
      x2 = x1;
      x1 = src[i];
      y2 = y1;
      y1 = v;
      y[i] = v;
    }
    return y;
  };
  const f = run(x);
  f.reverse();
  const r = run(f);
  return r.reverse();
}

// Sub-sample position of an extremum at index i (parabola through i-1, i, i+1).
function refine(x, i) {
  if (i <= 0 || i >= x.length - 1) return i;
  const a = x[i - 1];
  const b = x[i];
  const c = x[i + 1];
  const d = a - 2 * b + c;
  if (!d) return i;
  const off = (0.5 * (a - c)) / d;
  return Math.abs(off) <= 1 ? i + off : i;
}

function argmin(x, i0, i1) {
  let k = -1;
  let v = Infinity;
  for (let i = Math.max(0, i0); i < Math.min(x.length, i1); i++)
    if (x[i] < v) {
      v = x[i];
      k = i;
    }
  return k;
}

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const unit = (a) => {
  const n = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / n, a[1] / n, a[2] / n];
};

// Principal axis of a 3-axis signal (largest eigenvector of its covariance).
function principalAxis(cols, idx) {
  const C = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];
  const m = [0, 0, 0];
  for (const i of idx) for (let a = 0; a < 3; a++) m[a] += cols[a][i];
  for (let a = 0; a < 3; a++) m[a] /= idx.length || 1;
  for (const i of idx)
    for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) C[a][b] += (cols[a][i] - m[a]) * (cols[b][i] - m[b]);
  let v = [1, 1, 1].map((x, a) => x + a * 0.1);
  for (let it = 0; it < 60; it++) v = unit([dot(C[0], v), dot(C[1], v), dot(C[2], v)]);
  return v;
}

// ---------- resampling ----------

// Puts samples on a uniform grid (linear interpolation over lost samples and
// failed IMU reads). t ascending in seconds; channels may hold NaN.
export function resample(t, channels, fs) {
  const n = t.length;
  const t0 = t[0];
  const m = Math.max(0, Math.floor((t[n - 1] - t0) * fs) + 1);
  const grid = new Float64Array(m);
  for (let i = 0; i < m; i++) grid[i] = t0 + i / fs;
  const out = channels.map((x) => {
    const y = new Float64Array(m);
    let j = 0;
    let last = NaN;
    for (let i = 0; i < m; i++) {
      const tq = grid[i];
      while (j < n - 1 && t[j + 1] <= tq) j++;
      // nearest finite neighbours
      let a = j;
      while (a > 0 && !Number.isFinite(x[a])) a--;
      let b = Math.min(j + 1, n - 1);
      while (b < n - 1 && !Number.isFinite(x[b])) b++;
      const va = x[a];
      const vb = x[b];
      let v;
      if (Number.isFinite(va) && Number.isFinite(vb) && t[b] > t[a]) v = va + ((vb - va) * (tq - t[a])) / (t[b] - t[a]);
      else v = Number.isFinite(va) ? va : Number.isFinite(vb) ? vb : last;
      y[i] = Number.isFinite(v) ? v : 0;
      last = y[i];
    }
    return y;
  });
  return { t: grid, channels: out };
}

export function estimateRate(t) {
  const d = [];
  for (let i = 1; i < t.length; i++) if (t[i] > t[i - 1]) d.push(t[i] - t[i - 1]);
  const m = median(d);
  return m > 0 ? 1 / m : NaN;
}

// ---------- gait sequence detection (Ullrich-style) ----------

// Slides a window over the sagittal angular velocity and keeps windows that
// are active and whose spectrum has a clear dominant peak in the stride
// frequency band. Returns merged [i0, i1) index ranges.
export function detectSequences(w, fs, o = DEFAULTS) {
  // The signal is already low-passed, so ~25 Hz is plenty for this step.
  const dec = Math.max(1, Math.floor(fs / 25));
  const fd = fs / dec;
  const x = new Float64Array(Math.ceil(w.length / dec));
  for (let i = 0; i < x.length; i++) x[i] = w[i * dec];
  const win = Math.max(8, Math.round(o.seqWindowS * fd));
  const step = Math.max(1, Math.round(o.seqStepS * fd));
  const active = new Uint8Array(x.length);
  const freqs = [];
  for (let f = 0.1; f <= Math.min(6, fd / 2); f += 0.05) freqs.push(f);
  const lastStart = Math.max(0, x.length - win);
  const starts = [];
  for (let s = 0; s < lastStart; s += step) starts.push(s);
  starts.push(lastStart);
  for (const s of starts) {
    const e = Math.min(x.length, s + win);
    const { mean, sd } = meanSd(Array.from(x.subarray(s, e)));
    if (!(sd >= o.seqMinSd)) continue;
    let best = 0;
    let bestF = 0;
    let total = 0;
    for (const f of freqs) {
      // DFT at one frequency, rotating the phasor instead of calling cos/sin
      const k = (2 * Math.PI * f) / fd;
      const cr = Math.cos(k);
      const ci = Math.sin(k);
      let pr = 1;
      let pi = 0;
      let re = 0;
      let im = 0;
      for (let i = s; i < e; i++) {
        const v = x[i] - mean;
        re += v * pr;
        im -= v * pi;
        const t = pr * cr - pi * ci;
        pi = pr * ci + pi * cr;
        pr = t;
      }
      const p = re * re + im * im;
      total += p;
      if (p > best) {
        best = p;
        bestF = f;
      }
    }
    const prominence = best / (total / freqs.length || 1);
    // The fundamental of a shank signal is the stride frequency; the second
    // harmonic can dominate, so accept either landing in the band.
    const inBand = (bestF >= o.seqBand[0] && bestF <= o.seqBand[1]) || (bestF / 2 >= o.seqBand[0] && bestF / 2 <= o.seqBand[1]);
    if (inBand && prominence >= o.seqMinProminence) active.fill(1, s, e);
  }
  const seqs = [];
  let i = 0;
  while (i < x.length) {
    if (!active[i]) {
      i++;
      continue;
    }
    const a = i;
    while (i < x.length && active[i]) i++;
    seqs.push([a * dec, Math.min(w.length, i * dec)]);
  }
  return seqs;
}

// ---------- one leg ----------

// acc: [ax, ay, az] in g, gyr: [gx, gy, gz] in °/s, uniformly sampled at fs.
export function analyzeLeg(t, acc, gyr, fs, opts = {}) {
  const o = { ...DEFAULTS, ...opts };
  const n = t.length;
  const res = { fs, warnings: [], sequences: [], ms: [], ic: [], to: [], strides: [], w: new Float64Array(n), bias: 'none', axis: null };
  if (n < fs * 3) {
    res.warnings.push('Less than 3 s of data.');
    return res;
  }

  // 1. Bias: the stillest window (paper: resting baseline at the start).
  const rw = Math.max(4, Math.round(o.restWindowS * fs));
  let bestSd = Infinity;
  let bestAt = -1;
  for (let s = 0; s + rw <= n; s += Math.max(1, rw >> 2)) {
    let worst = 0;
    for (let a = 0; a < 3; a++) worst = Math.max(worst, meanSd(Array.from(gyr[a].subarray(s, s + rw))).sd);
    if (worst < bestSd) {
      bestSd = worst;
      bestAt = s;
    }
  }
  const bias = [0, 0, 0];
  if (bestSd <= o.restGyroSd) {
    for (let a = 0; a < 3; a++) bias[a] = meanSd(Array.from(gyr[a].subarray(bestAt, bestAt + rw))).mean;
    res.bias = `still window at ${(t[bestAt] - t[0]).toFixed(1)} s`;
  } else {
    res.warnings.push('No still moment found, so gyro offset was not removed. Stand still for a second or two at the start of each trial.');
  }

  // Clipped accelerometer samples would corrupt the integrated stride length.
  const sat = new Uint8Array(n);
  const lim = 0.98 * o.accelRangeG;
  for (let i = 0; i < n; i++) if (Math.abs(acc[0][i]) >= lim || Math.abs(acc[1][i]) >= lim || Math.abs(acc[2][i]) >= lim) sat[i] = 1;

  const fc = Math.min(8, 0.35 * fs);
  const g = gyr.map((x, a) => lowpass(x.map((v) => v - bias[a]), fs, fc));
  const ac = acc.map((x) => lowpass(x, fs, Math.min(15, 0.4 * fs)));

  // 2. Axis alignment: PCA on the gyro gives the medio-lateral axis.
  const all = [];
  for (let i = 0; i < n; i++) all.push(i);
  let m = principalAxis(g, all);
  let w = new Float64Array(n);
  for (let i = 0; i < n; i++) w[i] = m[0] * g[0][i] + m[1] * g[1][i] + m[2] * g[2][i];
  // Redo PCA on the active part only once it is known.
  let seqs = detectSequences(w, fs, o);
  if (seqs.length) {
    const idx = [];
    for (const [a, b] of seqs) for (let i = a; i < b; i++) idx.push(i);
    m = principalAxis(g, idx);
    for (let i = 0; i < n; i++) w[i] = m[0] * g[0][i] + m[1] * g[1][i] + m[2] * g[2][i];
  }
  // 3. Forward-direction correction: mid-swing peaks are the largest
  // excursions and point positive.
  const ref = seqs.length ? seqs.flatMap(([a, b]) => Array.from(w.subarray(a, b))) : Array.from(w);
  if (quantile(ref, 0.99) < -quantile(ref, 0.01)) {
    m = m.map((v) => -v);
    for (let i = 0; i < n; i++) w[i] = -w[i];
  }
  res.axis = m;
  res.w = w;
  seqs = detectSequences(w, fs, o);
  res.sequences = seqs.map(([a, b]) => [t[a], t[Math.min(b, n - 1)]]);
  if (!seqs.length) {
    res.warnings.push('No walking found in this stretch.');
    return res;
  }

  // 4. Events per sequence.
  const at = (x) => t[0] + x / fs; // fractional index to time
  for (const [a, b] of seqs) {
    // candidate mid-swing peaks
    let peaks = [];
    for (let i = Math.max(1, a); i < Math.min(n - 1, b); i++)
      if (w[i] > o.msMinDps && w[i] >= w[i - 1] && w[i] > w[i + 1]) peaks.push(i);
    const minGap = Math.round(0.35 * fs);
    peaks = suppress(peaks, w, minGap);
    if (peaks.length < 2) continue;
    const h = median(peaks.map((i) => w[i]));
    peaks = peaks.filter((i) => w[i] >= 0.4 * h);
    const T = median(peaks.slice(1).map((p, k) => p - peaks[k])) || fs;
    peaks = suppress(peaks, w, Math.round(0.5 * T));
    for (let k = 0; k < peaks.length; k++) {
      const p = peaks[k];
      const prev = k ? peaks[k - 1] : a - 1;
      const next = k + 1 < peaks.length ? peaks[k + 1] : b + Math.round(0.45 * T);
      // initial contact: the minimum within the ~40 % of a stride after mid-swing
      const ic = argmin(w, p + 1, Math.min(next, p + Math.round(0.45 * T), n));
      // toe-off: the minimum within the ~40 % of a stride before mid-swing
      const to = argmin(w, Math.max(prev + 1, p - Math.round(0.45 * T), 0), p);
      res.ms.push(at(p));
      res.ic.push(ic > 0 && ic < n - 1 && w[ic] < w[p] ? at(refine(w, ic)) : NaN);
      res.to.push(to > 0 && w[to] < w[p] ? at(refine(w, to)) : NaN);
    }
    res.ms.push(NaN); // sequence break
    res.ic.push(NaN);
    res.to.push(NaN);
  }

  // 5. Strides: Eqs. 1–3 of the first paper.
  //   stride(i) = HS(i+1) − HS(i); stance(i) = TO(i) − HS(i); swing(i) = HS(i+1) − TO(i)
  for (let k = 0; k + 1 < res.ms.length; k++) {
    const hs = res.ic[k];
    const hsNext = res.ic[k + 1];
    const to = res.to[k + 1];
    if (![hs, hsNext, to].every(Number.isFinite)) continue;
    if (!(to > hs && to < hsNext)) continue;
    const strideT = hsNext - hs;
    const stanceT = to - hs;
    const swingT = hsNext - to;
    const stancePct = (100 * stanceT) / strideT;
    if (strideT < o.strideTRange[0] || strideT > o.strideTRange[1]) continue;
    if (stancePct < o.stancePctRange[0] || stancePct > o.stancePctRange[1]) continue;
    res.strides.push({ hs, to, hsNext, strideT, stanceT, swingT, stancePct, swingPct: 100 - stancePct, length: NaN, speed: NaN });
  }

  // 6. Stride length: integrate between mid-stance instants.
  const clipped = strideLengths(res, t, ac, g, m, fs, sat);
  if (clipped)
    res.warnings.push(`The accelerometer hit its ±${o.accelRangeG} g limit in ${clipped} stride${clipped > 1 ? 's' : ''}, so ${clipped > 1 ? 'they have' : 'it has'} no sensor stride length.`);
  return res;
}

function suppress(peaks, w, gap) {
  // keep the tallest peak within any gap-sized neighbourhood
  const order = peaks.slice().sort((a, b) => w[b] - w[a]);
  const kept = [];
  for (const p of order) if (kept.every((q) => Math.abs(q - p) >= gap)) kept.push(p);
  return kept.sort((a, b) => a - b);
}

// Mid-stance: the stillest sample in the middle of stance (smallest gyro norm).
function midStance(t, g, fs, hs, to) {
  const i0 = Math.ceil((hs - t[0]) * fs + 0.15 * (to - hs) * fs);
  const i1 = Math.floor((hs - t[0]) * fs + 0.75 * (to - hs) * fs);
  let k = -1;
  let v = Infinity;
  for (let i = Math.max(0, i0); i <= Math.min(t.length - 1, i1); i++) {
    const s = g[0][i] ** 2 + g[1][i] ** 2 + g[2][i] ** 2;
    if (s < v) {
      v = s;
      k = i;
    }
  }
  return k;
}

function strideLengths(res, t, ac, g, m, fs, sat) {
  const n = t.length;
  let clipped = 0;
  if (!res.strides.length) return clipped;
  // Sagittal plane basis: m = medio-lateral (rotation axis), u = mean
  // acceleration projected off m (roughly up), f = u × m (forward or back).
  const mean = [0, 0, 0];
  for (let a = 0; a < 3; a++) {
    for (let i = 0; i < n; i++) mean[a] += ac[a][i];
    mean[a] /= n;
  }
  const d = dot(mean, m);
  const u = unit([mean[0] - d * m[0], mean[1] - d * m[1], mean[2] - d * m[2]]);
  const f = cross(u, m);
  const af = new Float64Array(n);
  const au = new Float64Array(n);
  const wm = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const v = [ac[0][i], ac[1][i], ac[2][i]];
    af[i] = dot(v, f);
    au[i] = dot(v, u);
    wm[i] = (m[0] * g[0][i] + m[1] * g[1][i] + m[2] * g[2][i]) * RAD;
  }
  // mid-stance of each stride's own stance, and of the next stride's stance
  const strides = res.strides;
  for (let k = 0; k < strides.length; k++) {
    const s = strides[k];
    const nx = strides[k + 1];
    if (!nx || Math.abs(nx.hs - s.hsNext) > 1e-9) continue; // need the following stance
    const i0 = midStance(t, g, fs, s.hs, s.to);
    const i1 = midStance(t, g, fs, nx.hs, nx.to);
    if (i0 < 0 || i1 <= i0 + 2) continue;
    if (sat.subarray(i0, i1 + 1).some((x) => x)) {
      clipped++;
      continue;
    }
    s.length = integrateStride(af, au, wm, fs, i0, i1);
    s.speed = s.length / s.strideT;
  }
  return clipped;
}

// De-drifted 2D strapdown integration in the sagittal plane between two
// zero-velocity instants i0 and i1. Returns the horizontal distance in m.
function integrateStride(af, au, wm, fs, i0, i1) {
  const dt = 1 / fs;
  const L = i1 - i0;
  // inclination at both ends from gravity
  const th0 = Math.atan2(af[i0], au[i0]);
  const th1 = Math.atan2(af[i1], au[i1]);
  // integrate the gyro, then spread the mismatch linearly (removes bias)
  const th = new Float64Array(L + 1);
  th[0] = th0;
  for (let j = 1; j <= L; j++) th[j] = th[j - 1] + 0.5 * (wm[i0 + j - 1] + wm[i0 + j]) * dt;
  const drift = th[L] - th1;
  for (let j = 0; j <= L; j++) th[j] -= (drift * j) / L;
  // world acceleration (gravity removed), then velocity
  const vf = new Float64Array(L + 1);
  const vu = new Float64Array(L + 1);
  let pf = 0;
  let pu = 0;
  let prevF = 0;
  let prevU = 0;
  for (let j = 0; j <= L; j++) {
    const c = Math.cos(th[j]);
    const s = Math.sin(th[j]);
    const f = (c * af[i0 + j] - s * au[i0 + j]) * G;
    const uu = (s * af[i0 + j] + c * au[i0 + j]) * G - G;
    if (j) {
      vf[j] = vf[j - 1] + 0.5 * (prevF + f) * dt;
      vu[j] = vu[j - 1] + 0.5 * (prevU + uu) * dt;
    }
    prevF = f;
    prevU = uu;
  }
  // zero velocity at both ends: remove the linear drift
  for (let j = 0; j <= L; j++) {
    vf[j] -= (vf[L] * j) / L;
    vu[j] -= (vu[L] * j) / L;
  }
  for (let j = 1; j <= L; j++) {
    pf += 0.5 * (vf[j - 1] + vf[j]) * dt;
    pu += 0.5 * (vu[j - 1] + vu[j]) * dt;
  }
  return Math.abs(pf);
}

// ---------- both legs ----------

// src: {n, t(i), v(key, i)} with keys 6..11 = IMU A ax..gz and 12..17 = IMU B
// (g and °/s), as the app's live buffer and recording sources provide.
// sides: {A: 'right'|'left'|'off', B: ...}; distanceM: walked distance for Eq. 4.
export function analyzeSource(src, { t0 = -Infinity, t1 = Infinity, imuMask = 3, sides = { A: 'right', B: 'left' }, distanceM = 0, accelRangeG = 8, opts = {} } = {}) {
  let i0 = 0;
  while (i0 < src.n && src.t(i0) < t0) i0++;
  let i1 = i0;
  while (i1 < src.n && src.t(i1) <= t1) i1++;
  const out = { legs: {}, warnings: [], fs: NaN, t: null, combined: null };
  if (i1 - i0 < 10) {
    out.warnings.push('Not enough samples yet.');
    return out;
  }
  const traw = new Float64Array(i1 - i0);
  for (let i = i0; i < i1; i++) traw[i - i0] = src.t(i);
  const fs = estimateRate(traw);
  out.fs = fs;
  if (!(fs > 0)) return out;
  if (fs < 50)
    out.warnings.push(
      `The stream is ${fs.toFixed(0)} samples per second; the papers used 100. Event times are interpolated between samples, but expect about ±${Math.round(500 / fs)} ms of extra timing error. Raise the Bluetooth module to 115200 baud (README, "Bluetooth speed") for ~245 per second.`,
    );
  for (const [k, name] of [[0, 'A'], [1, 'B']]) {
    const side = sides[name];
    if (!(imuMask & (1 << k)) || side === 'off') continue;
    const chans = [];
    for (let a = 0; a < 6; a++) {
      const x = new Float64Array(i1 - i0);
      for (let i = i0; i < i1; i++) x[i - i0] = src.v(6 + k * 6 + a, i);
      chans.push(x);
    }
    const r = resample(traw, chans, fs);
    out.t = r.t;
    const leg = analyzeLeg(r.t, r.channels.slice(0, 3), r.channels.slice(3, 6), fs, { accelRangeG, ...opts });
    leg.imu = name;
    leg.side = side;
    out.legs[side in out.legs ? `${side}-${name}` : side] = leg;
  }
  out.combined = combine(out.legs, distanceM);
  return out;
}

function legSummary(leg) {
  const s = leg.strides;
  const pick = (k) => meanSd(s.map((x) => x[k]));
  const strideT = pick('strideT');
  return {
    strides: s.length,
    strideT,
    stanceT: pick('stanceT'),
    swingT: pick('swingT'),
    stancePct: pick('stancePct'),
    swingPct: pick('swingPct'),
    cadenceStrides: strideT.n ? 60 / strideT.mean : NaN, // strides per minute (paper's definition)
    strideCv: strideT.n > 1 ? (100 * strideT.sd) / strideT.mean : NaN,
    length: pick('length'),
    speed: pick('speed'),
  };
}

const si = (a, b) => (Number.isFinite(a) && Number.isFinite(b) && a + b ? (200 * Math.abs(a - b)) / (a + b) : NaN);

export function combine(legs, distanceM) {
  const names = Object.keys(legs);
  const sum = {};
  for (const k of names) sum[k] = legSummary(legs[k]);
  const all = names.flatMap((k) => legs[k].strides);
  const c = {
    perLeg: sum,
    strides: all.length,
    strideT: meanSd(all.map((s) => s.strideT)),
    stanceT: meanSd(all.map((s) => s.stanceT)),
    swingT: meanSd(all.map((s) => s.swingT)),
    stancePct: meanSd(all.map((s) => s.stancePct)),
    swingPct: meanSd(all.map((s) => s.swingPct)),
    sensorLength: meanSd(all.map((s) => s.length)),
    sensorSpeed: meanSd(all.map((s) => s.speed)),
    stepT: meanSd([]),
    doubleSupportPct: meanSd([]),
    cadenceSteps: NaN,
    cadenceStrides: NaN,
    walkTimeS: NaN,
    meanStrideLength: NaN, // Eq. 4, needs a known distance
    gaitSpeed: NaN,
    symmetry: {},
  };
  if (c.strideT.n) {
    c.cadenceStrides = 60 / c.strideT.mean;
    c.cadenceSteps = 2 * c.cadenceStrides;
  }
  // Bilateral parameters need one leg each side.
  const L = legs.left;
  const R = legs.right;
  if (L && R) {
    const steps = [];
    const ds = [];
    for (const [ip, ct] of [[L, R], [R, L]]) {
      const cIc = ct.strides.flatMap((s) => [s.hs, s.hsNext]).filter((v, i, a) => a.indexOf(v) === i);
      const cTo = ct.strides.map((s) => s.to);
      for (const s of ip.strides) {
        // step: from this heel strike to the next contralateral one
        const nextC = cIc.find((x) => x > s.hs && x < s.hsNext);
        if (nextC !== undefined) steps.push(nextC - s.hs);
        // initial double support ends at the contralateral toe-off; terminal
        // double support runs from the contralateral heel strike to this toe-off
        const cto = cTo.find((x) => x > s.hs && x < s.to);
        if (cto !== undefined && nextC !== undefined && nextC < s.to)
          ds.push((100 * (cto - s.hs + (s.to - nextC))) / s.strideT);
      }
    }
    c.stepT = meanSd(steps);
    c.doubleSupportPct = meanSd(ds);
    if (c.stepT.n) c.cadenceSteps = 60 / c.stepT.mean;
    const sl = legSummary(L);
    const sr = legSummary(R);
    c.symmetry = {
      strideT: si(sl.strideT.mean, sr.strideT.mean),
      stanceT: si(sl.stanceT.mean, sr.stanceT.mean),
      swingT: si(sl.swingT.mean, sr.swingT.mean),
      length: si(sl.length.mean, sr.length.mean),
    };
  }
  // Eq. 4 and gait speed over a measured walk (e.g. the 10 m walk test):
  // walking time from the first to the last heel strike seen on either leg,
  // strides = walking time / mean stride time.
  if (all.length) {
    const hs = all.flatMap((s) => [s.hs, s.hsNext]);
    c.walkTimeS = Math.max(...hs) - Math.min(...hs);
    if (distanceM > 0 && c.walkTimeS > 0) {
      const nStrides = c.walkTimeS / c.strideT.mean;
      c.meanStrideLength = distanceM / nStrides;
      c.gaitSpeed = distanceM / c.walkTimeS;
    }
  }
  return c;
}

// One row per stride, for CSV export.
export function stridesCsv(result, name = '') {
  const head = ['leg', 'imu', 'stride', 'hs_s', 'to_s', 'next_hs_s', 'stride_s', 'stance_s', 'swing_s', 'stance_pct', 'swing_pct', 'stride_length_m', 'stride_speed_m_s'];
  const lines = [`# gait strides${name ? ` for ${name}` : ''}; heel strike (HS) = initial contact, TO = toe-off; length/speed from the ankle sensor (de-drifted integration)`, head.join(',')];
  for (const [side, leg] of Object.entries(result.legs))
    leg.strides.forEach((s, i) => {
      lines.push(
        [side, leg.imu, i + 1, s.hs.toFixed(3), s.to.toFixed(3), s.hsNext.toFixed(3), s.strideT.toFixed(3), s.stanceT.toFixed(3), s.swingT.toFixed(3), s.stancePct.toFixed(1), s.swingPct.toFixed(1), Number.isFinite(s.length) ? s.length.toFixed(3) : '', Number.isFinite(s.speed) ? s.speed.toFixed(3) : ''].join(','),
      );
    });
  return lines.join('\n') + '\n';
}
