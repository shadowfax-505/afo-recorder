// Stride segmentation with gaitmap's pre-trained hidden Markov model.
//
// SPDX-License-Identifier: AGPL-3.0-or-later
// This file is a port of gaitmap_mad code, Copyright (C) 2022 MaD-Lab
// Erlangen, and is distributed under the same licence (licenses/
// gaitmap-LICENSE.txt and licenses/AGPL-3.0.txt at the repo root). If you
// serve this web app to other people, the AGPL asks you to offer them its
// source; this public repository does that.
//
// A JavaScript port of the prediction path of gaitmap's HmmStrideSegmentation
// with PreTrainedRothSegmentationModel (gaitmap / gaitmap_mad 2.6.0,
// AGPL-3.0-or-later, Machine Learning and Data Analytics Lab, FAU), which is
// the model of Roth et al., J NeuroEng Rehabil 18, 93 (2021). The trained
// numbers live in models/roth-hmm.js, exported unchanged from gaitmap's
// fallriskpd_at_lab_model.json by host/tools/export_gaitmap_hmm.py.
//
// The steps, each matching the gaitmap code it ports:
//   1. 4th-order Butterworth low-pass at 10 Hz, forward-backward
//      (ButterworthFilter -> scipy sosfiltfilt, odd padding, steady-state start)
//   2. FFT resampling to 51.2 Hz (Resample -> scipy.signal.resample)
//   3. features: the signal itself and its slope over a centred 0.2 s window
//      (IdentityTransformer, SlidingWindowGradient), then each feature
//      z-scored over the whole recording (sklearn preprocessing.scale)
//   4. Viterbi decoding through 5 "transition" states and 20 "stride" states,
//      each emitting a 2-D Gaussian mixture (pomegranate HiddenMarkovModel)
//   5. states back to the input rate by nearest neighbour, a stride is each
//      entry into the first stride state up to the exit from the last
//   6. each border snapped to the gyr_ml minimum within ±50 ms
//
// gyr_ml is gaitmap's medio-lateral gyro axis. In gaitmap's foot frame the
// swing phase is a large POSITIVE peak and a stride runs from one pre-swing
// minimum (about toe-off) to the next. This app's sagittal signal w has the
// same sign (swing positive), so it is passed as it is.
//
// The model was trained on foot-mounted sensors of people with Parkinson's
// disease in a lab. Our sensors are on the shank; the swing-peak pattern is
// similar but not the same, so treat its output as an alternative stride
// finder to compare against the peak rules, not as validated for this setup.

import ROTH from './models/roth-hmm.js';

export const MODEL = ROTH;

// ---------- filter: scipy.signal.butter(..., output='sos') + sosfiltfilt ----------

export function butterLowpassSos(order, fc, fs) {
  // analog prototype poles, prewarp, bilinear transform (scipy iirfilter)
  const warped = 4 * Math.tan((Math.PI * (2 * fc / fs)) / 2);
  const poles = [];
  for (let m = -order + 1; m < order; m += 2) {
    const ang = (Math.PI * m) / (2 * order);
    // p = -exp(j ang) * warped
    const pr = -Math.cos(ang) * warped;
    const pi = -Math.sin(ang) * warped;
    // z = (4 + p) / (4 - p)
    const nr = 4 + pr, ni = pi, dr = 4 - pr, di = -pi;
    const den = dr * dr + di * di;
    poles.push([(nr * dr + ni * di) / den, (ni * dr - nr * di) / den]);
  }
  // overall gain so that DC gain is 1 (equivalent to scipy's k)
  const sections = [];
  const upper = poles.filter((p) => p[1] > 1e-12).sort((a, b) => Math.hypot(...a) - Math.hypot(...b));
  for (const [re, im] of upper) sections.push([1, 2, 1, 1, -2 * re, re * re + im * im]);
  if (order % 2) {
    const real = poles.find((p) => Math.abs(p[1]) <= 1e-12);
    sections.unshift([1, 1, 0, 1, -real[0], 0]);
  }
  let k = 1;
  for (const s of sections) k *= (s[3] + s[4] + s[5]) / (s[0] + s[1] + s[2]);
  for (let i = 0; i < 3; i++) sections[0][i] *= k;
  return sections;
}

function sosfiltZi(sos) {
  let scale = 1;
  return sos.map(([b0, b1, b2, , a1, a2]) => {
    const B0 = b1 - a1 * b0;
    const B1 = b2 - a2 * b0;
    const z0 = (B0 + B1) / (1 + a1 + a2);
    const z = [scale * z0, scale * (B1 - a2 * z0)];
    scale *= (b0 + b1 + b2) / (1 + a1 + a2);
    return z;
  });
}

function sosfilt(sos, x, zi) {
  const y = Float64Array.from(x);
  sos.forEach(([b0, b1, b2, , a1, a2], s) => {
    let [z0, z1] = zi[s];
    for (let i = 0; i < y.length; i++) {
      const xi = y[i];
      const yi = b0 * xi + z0;
      z0 = b1 * xi - a1 * yi + z1;
      z1 = b2 * xi - a2 * yi;
      y[i] = yi;
    }
  });
  return y;
}

export function sosfiltfilt(sos, x) {
  const n = x.length;
  const nz = Math.min(sos.filter((s) => s[2] === 0).length, sos.filter((s) => s[5] === 0).length);
  const pad = Math.min(3 * (2 * sos.length + 1 - nz), n - 1);
  const ext = new Float64Array(n + 2 * pad);
  for (let i = 0; i < pad; i++) ext[i] = 2 * x[0] - x[pad - i];
  ext.set(x, pad);
  for (let i = 0; i < pad; i++) ext[pad + n + i] = 2 * x[n - 1] - x[n - 2 - i];
  const zi = sosfiltZi(sos);
  let y = sosfilt(sos, ext, zi.map((z) => z.map((v) => v * ext[0])));
  y.reverse();
  y = sosfilt(sos, y, zi.map((z) => z.map((v) => v * y[0])));
  y.reverse();
  return y.slice(pad, pad + n);
}

// ---------- FFT (radix 2, Bluestein for other lengths) ----------

function fft2(re, im, inverse) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = ((inverse ? 2 : -2) * Math.PI) / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const tr = re[b] * cr - im[b] * ci;
        const ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr;
        im[b] = im[a] - ti;
        re[a] += tr;
        im[a] += ti;
        const nr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = nr;
      }
    }
  }
}

// In-place DFT of any length; inverse is unscaled.
export function fft(re, im, inverse = false) {
  const n = re.length;
  if (!(n & (n - 1))) return fft2(re, im, inverse);
  let m = 1;
  while (m < 2 * n - 1) m <<= 1;
  const s = inverse ? 1 : -1;
  const cr = new Float64Array(n), ci = new Float64Array(n);
  for (let k = 0; k < n; k++) {
    const a = (s * Math.PI * ((k * k) % (2 * n))) / n;
    cr[k] = Math.cos(a);
    ci[k] = Math.sin(a);
  }
  const ar = new Float64Array(m), ai = new Float64Array(m);
  const br = new Float64Array(m), bi = new Float64Array(m);
  for (let k = 0; k < n; k++) {
    ar[k] = re[k] * cr[k] - im[k] * ci[k];
    ai[k] = re[k] * ci[k] + im[k] * cr[k];
  }
  br[0] = cr[0];
  bi[0] = -ci[0];
  for (let k = 1; k < n; k++) {
    br[k] = br[m - k] = cr[k];
    bi[k] = bi[m - k] = -ci[k];
  }
  fft2(ar, ai, false);
  fft2(br, bi, false);
  for (let k = 0; k < m; k++) {
    const r = ar[k] * br[k] - ai[k] * bi[k];
    ai[k] = ar[k] * bi[k] + ai[k] * br[k];
    ar[k] = r;
  }
  fft2(ar, ai, true);
  for (let k = 0; k < n; k++) {
    const r = ar[k] / m, i = ai[k] / m;
    re[k] = r * cr[k] - i * ci[k];
    im[k] = r * ci[k] + i * cr[k];
  }
}

// scipy.signal.resample for a real signal.
export function fftResample(x, num) {
  const nx = x.length;
  const re = Float64Array.from(x), im = new Float64Array(nx);
  fft(re, im);
  const N = Math.min(num, nx);
  const nyq = Math.floor(N / 2) + 1;
  const half = Math.floor(num / 2) + 1;
  const Yr = new Float64Array(half), Yi = new Float64Array(half);
  for (let k = 0; k < Math.min(nyq, half); k++) {
    Yr[k] = re[k];
    Yi[k] = im[k];
  }
  if (N % 2 === 0) {
    const f = num < nx ? 2 : num > nx ? 0.5 : 1;
    if (N / 2 < half) {
      Yr[N / 2] *= f;
      Yi[N / 2] *= f;
    }
  }
  // irfft(Y, num)
  const zr = new Float64Array(num), zi = new Float64Array(num);
  for (let k = 0; k < half; k++) {
    zr[k] = Yr[k];
    zi[k] = Yi[k];
    if (k > 0 && num - k !== k) {
      zr[num - k] = Yr[k];
      zi[num - k] = -Yi[k];
    }
  }
  zi[0] = 0;
  if (num % 2 === 0) zi[num / 2] = 0;
  fft(zr, zi, true);
  const y = new Float64Array(num);
  for (let i = 0; i < num; i++) y[i] = (zr[i] / num) * (num / nx);
  return y;
}

// ---------- feature space ----------

export function features(gyrMl, fs, model = ROTH) {
  if (fs < model.featureSpaceHz)
    throw new Error(`The trained stride model needs at least ${model.featureSpaceHz} samples per second; this data has ${fs.toFixed(1)}.`);
  const filtered = sosfiltfilt(butterLowpassSos(model.lowPass.order, model.lowPass.cutoffHz, fs), gyrMl);
  const n = Math.round((gyrMl.length * model.featureSpaceHz) / fs);
  const raw = fs === model.featureSpaceHz ? filtered : fftResample(filtered, n);
  let win = Math.round(model.featureSpaceHz * model.windowS);
  if (win % 2 === 0) win += 1;
  const h = (win - 1) / 2;
  let den = 0;
  for (let j = -h; j <= h; j++) den += j * j;
  const grad = new Float64Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    let s = 0;
    for (let j = -h; j <= h; j++) {
      const k = i + j;
      if (k >= 0 && k < raw.length) s += j * raw[k]; // zero padding outside
    }
    grad[i] = s / den;
  }
  const cols = [raw, grad];
  if (model.standardize)
    for (const c of cols) {
      let m = 0;
      for (const v of c) m += v;
      m /= c.length;
      let v2 = 0;
      for (const v of c) v2 += (v - m) ** 2;
      const sd = Math.sqrt(v2 / c.length) || 1;
      for (let i = 0; i < c.length; i++) c[i] = (c[i] - m) / sd;
    }
  return cols;
}

// ---------- emissions and Viterbi ----------

function prepare(model) {
  if (model._prep) return model._prep;
  const comps = model.states.map((s) =>
    s.comps.map(({ w, mean, cov }) => {
      const [[a, b], [, d]] = cov;
      const det = a * d - b * b;
      return { lw: Math.log(w), mean, inv: [d / det, -b / det, a / det], c: -Math.log(2 * Math.PI) - 0.5 * Math.log(det) };
    }),
  );
  const lt = model.trans.map((row) => row.map(Math.log));
  const ls = model.start.map(Math.log);
  model._prep = { comps, lt, ls };
  return model._prep;
}

export function viterbi(cols, model = ROTH) {
  const { comps, lt, ls } = prepare(model);
  const S = model.states.length;
  const T = cols[0].length;
  const emit = new Float64Array(S);
  const back = new Int16Array(T * S);
  let v = new Float64Array(S), nv = new Float64Array(S);
  const emissions = (t) => {
    const x = cols[0][t], y = cols[1][t];
    for (let s = 0; s < S; s++) {
      let mx = -Infinity;
      const parts = comps[s].map(({ lw, mean, inv, c }) => {
        const dx = x - mean[0], dy = y - mean[1];
        const q = lw + c - 0.5 * (inv[0] * dx * dx + 2 * inv[1] * dx * dy + inv[2] * dy * dy);
        if (q > mx) mx = q;
        return q;
      });
      let sum = 0;
      for (const q of parts) sum += Math.exp(q - mx);
      emit[s] = mx + Math.log(sum);
    }
  };
  emissions(0);
  for (let s = 0; s < S; s++) v[s] = ls[s] + emit[s];
  for (let t = 1; t < T; t++) {
    emissions(t);
    for (let j = 0; j < S; j++) {
      let best = -Infinity, arg = 0;
      for (let i = 0; i < S; i++) {
        const p = v[i] + lt[i][j];
        if (p > best) {
          best = p;
          arg = i;
        }
      }
      nv[j] = best + emit[j];
      back[t * S + j] = arg;
    }
    [v, nv] = [nv, v];
  }
  let last = 0;
  for (let s = 1; s < S; s++) if (v[s] > v[last]) last = s;
  const path = new Int16Array(T);
  path[T - 1] = last;
  for (let t = T - 1; t > 0; t--) path[t - 1] = back[t * S + path[t]];
  return { path, logp: v[last] };
}

// ---------- full segmentation ----------

// gyrMl: gaitmap-convention medio-lateral gyro (swing positive), any unit.
// Returns {strides: [[start, end]] sample indices (end exclusive, like
// gaitmap), states (per input sample), featureStates, features}.
export function segment(gyrMl, fs, { model = ROTH, snapMs = 100 } = {}) {
  const N = gyrMl.length;
  const cols = features(gyrMl, fs, model);
  if (cols[0].length < model.states.length) return { strides: [], states: new Int16Array(N), featureStates: new Int16Array(0), features: cols };
  // gaitmap drops the last decoded label along with pomegranate's start label
  const featureStates = viterbi(cols, model).path.slice(0, -1);
  // back to the input rate: scipy interp1d(kind='nearest') at arange(0, N-1, N/M)
  const M = featureStates.length;
  const step = N / M;
  const xs = [];
  for (let x = 0; x < N - 1; x += step) xs.push(x);
  const states = new Int16Array(N);
  let k = 0;
  for (let i = 0; i < N; i++) {
    while (k + 1 < xs.length && (xs[k] + xs[k + 1]) / 2 < i) k++;
    states[i] = featureStates[Math.min(k, M - 1)];
  }
  const first = model.transitionStates;
  const lastS = model.transitionStates + model.strideStates - 1;
  const starts = [], ends = [];
  if (states[0] === first) starts.push(0);
  for (let i = 1; i < N; i++) {
    if (states[i] === first && states[i - 1] !== first) starts.push(i);
    if (states[i - 1] === lastS && states[i] !== lastS) ends.push(i);
  }
  if (states[N - 1] === lastS) ends.push(N);
  let matches = [];
  const seenEnd = new Set();
  for (const s of starts) {
    const e = ends.find((x) => x > s);
    if (e === undefined || seenEnd.has(e)) continue;
    seenEnd.add(e);
    matches.push([s, e]);
  }
  // snap to the closest gyr_ml minimum (gaitmap snap_to_min)
  const r = Math.floor(Math.trunc((snapMs / 1000) * fs) / 2);
  if (snapMs && r > 0)
    matches = matches.map((pair) =>
      pair.map((idx) => {
        const edge = idx === N;
        const c = edge ? N - 1 : idx;
        let best = Infinity, at = c;
        for (let i = Math.max(0, c - r); i <= Math.min(N - 1, c + r); i++)
          if (gyrMl[i] < best) {
            best = gyrMl[i];
            at = i;
          }
        return edge && at === N - 1 ? N : at;
      }),
    );
  return { strides: matches, states, featureStates, features: cols };
}
