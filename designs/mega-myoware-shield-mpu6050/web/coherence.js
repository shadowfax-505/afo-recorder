// Coherence between two raw EMG channels (ESP32 firmware 1.3+, 2 kHz).
//
// Why: two electrode pairs on the same muscle (tibialis anterior, proximal and
// distal, at least 10 cm apart) pick up different motor units. If the spinal
// motor neurons of those units receive a common rhythmic input, the two
// signals are coherent at that rhythm. Coherence at 15-55 Hz during swing is
// used as a marker of common descending (largely corticospinal) drive to the
// ankle dorsiflexors (Halliday et al. 1995 for the method; walking protocol
// after Zipser-Mohammadzada et al. 2023: 2 kHz, 15-55 Hz, swing phase).
//
// Method (the "pooled segments" estimate):
//   1. Each channel is high-pass filtered (zero-phase, 20 Hz by default) to
//      remove the offset and movement artefact, then full-wave rectified
//      (optional). Rectifying brings the motor-unit firing rhythm down from
//      the shape of the action potentials into the 10-60 Hz range.
//   2. Inside each analysis window (for example every swing phase) the signals
//      are cut into non-overlapping segments of segLen samples. Segments that
//      contain a lost sample are dropped.
//   3. Each segment has its mean removed, is tapered (Hann) and transformed.
//      The auto-spectra Sxx, Syy and the cross-spectrum Sxy are averaged over
//      all L segments.
//   4. Coherence C(f) = |Sxy|^2 / (Sxx * Syy), between 0 and 1.
//      Under the hypothesis of independent signals, C stays below
//      1 - 0.05^(1 / (L - 1)) at 95 % of frequencies.
//   5. The cumulant density (inverse transform of Sxy, scaled like a
//      correlation coefficient) shows the time lag of the common part. A
//      narrow peak at exactly 0 ms with broadband coherence is what electrical
//      cross-talk, a shared reference or supply noise look like; physiological
//      coupling between sites 10 cm apart is usually a few ms wide and band
//      limited.
//
// What it cannot tell apart by itself: common neural drive, cross-talk, mains
// (50/60 Hz, inside the band of interest) and noise shared through the ADC
// reference. That is what the bench checks in docs/coherence-bench-checks.md
// are for; this file only does the arithmetic.

export const COH_DEFAULTS = {
  segLen: 512, // samples; 256 ms and 3.9 Hz resolution at 2 kHz
  rectify: true,
  hpHz: 20,
  band: [15, 55],
  mainsHz: 50,
  mainsHalfWidthHz: 2,
  maxLagMs: 50,
};

// In-place radix-2 FFT. inverse = true gives the unscaled inverse.
export function fft(re, im, inverse = false) {
  const n = re.length;
  if (n & (n - 1)) throw new Error('FFT length must be a power of two');
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
    const wr = Math.cos(ang);
    const wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1;
      let ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k;
        const b = a + len / 2;
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

// Zero-phase 2nd-order Butterworth high-pass (forward and backward: 4th-order
// magnitude, no time shift).
export function highpass(x, fc, fs) {
  if (!(fc > 0)) return Float64Array.from(x);
  const k = Math.tan((Math.PI * fc) / fs);
  const q = Math.SQRT1_2;
  const norm = 1 / (1 + k / q + k * k);
  const b0 = norm;
  const b1 = -2 * norm;
  const a1 = 2 * (k * k - 1) * norm;
  const a2 = (1 - k / q + k * k) * norm;
  const pass = (src) => {
    const out = new Float64Array(src.length);
    // start in the steady state for a constant input equal to the first sample
    let z1 = -b0 * src[0];
    let z2 = b0 * src[0];
    for (let i = 0; i < src.length; i++) {
      const y = b0 * src[i] + z1;
      z1 = b1 * src[i] - a1 * y + z2;
      z2 = b0 * src[i] - a2 * y;
      out[i] = y;
    }
    return out;
  };
  const fwd = pass(x).reverse();
  return pass(fwd).reverse();
}

// 95 % confidence limit for coherence from L independent segments.
export function confidenceLimit(L, alpha = 0.05) {
  return L > 1 ? 1 - alpha ** (1 / (L - 1)) : 1;
}

// x, y: equally long arrays sampled at fs (ADC counts or volts).
// opts.windows: [[t0, t1], ...] in seconds from the first sample; null = all.
// opts.valid: optional Uint8Array, 0 where a sample is missing.
export function coherence(x, y, fs, opts = {}) {
  const o = { ...COH_DEFAULTS, ...opts };
  const N = o.segLen;
  const n = Math.min(x.length, y.length);
  const warnings = [];
  const prep = (v) => {
    const h = highpass(v, o.hpHz, fs);
    if (o.rectify) for (let i = 0; i < h.length; i++) h[i] = Math.abs(h[i]);
    return h;
  };
  const px = prep(x);
  const py = prep(y);
  const hann = Float64Array.from({ length: N }, (_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / N));
  const half = N / 2;
  const sxx = new Float64Array(half + 1);
  const syy = new Float64Array(half + 1);
  const sxyRe = new Float64Array(N);
  const sxyIm = new Float64Array(N);
  let L = 0;
  let skipped = 0;
  let sumSqX = 0;
  let sumSqY = 0;
  const windows = o.windows || [[0, n / fs]];
  const xr = new Float64Array(N);
  const xi = new Float64Array(N);
  const yr = new Float64Array(N);
  const yi = new Float64Array(N);
  for (const [t0, t1] of windows) {
    const i0 = Math.max(0, Math.ceil(t0 * fs));
    const i1 = Math.min(n, Math.floor(t1 * fs));
    for (let s = i0; s + N <= i1; s += N) {
      let ok = true;
      if (o.valid) for (let i = s; i < s + N; i++) if (!o.valid[i]) { ok = false; break; }
      if (!ok) {
        skipped++;
        continue;
      }
      let mx = 0;
      let my = 0;
      for (let i = 0; i < N; i++) {
        mx += px[s + i];
        my += py[s + i];
      }
      mx /= N;
      my /= N;
      for (let i = 0; i < N; i++) {
        const a = px[s + i] - mx;
        const b = py[s + i] - my;
        sumSqX += a * a;
        sumSqY += b * b;
        xr[i] = a * hann[i];
        yr[i] = b * hann[i];
        xi[i] = 0;
        yi[i] = 0;
      }
      fft(xr, xi);
      fft(yr, yi);
      for (let k = 0; k < N; k++) {
        // Sxy = conj(X) * Y: a positive lag means y follows x
        sxyRe[k] += xr[k] * yr[k] + xi[k] * yi[k];
        sxyIm[k] += xr[k] * yi[k] - xi[k] * yr[k];
        if (k <= half) {
          sxx[k] += xr[k] * xr[k] + xi[k] * xi[k];
          syy[k] += yr[k] * yr[k] + yi[k] * yi[k];
        }
      }
      L++;
    }
  }
  const f = Float64Array.from({ length: half + 1 }, (_, k) => (k * fs) / N);
  const coh = new Float64Array(half + 1);
  const phase = new Float64Array(half + 1);
  for (let k = 0; k <= half; k++) {
    const d = sxx[k] * syy[k];
    coh[k] = d > 0 ? (sxyRe[k] * sxyRe[k] + sxyIm[k] * sxyIm[k]) / d : 0;
    phase[k] = Math.atan2(sxyIm[k], sxyRe[k]);
  }
  const cl95 = confidenceLimit(L);
  if (L < 20) warnings.push(`Only ${L} segments: the estimate is rough. Aim for 100 or more (about 100 strides when analysing swing).`);
  if (skipped) warnings.push(`${skipped} segments dropped because samples were lost inside them.`);

  // band summary
  const df = fs / N;
  const band = { lo: o.band[0], hi: o.band[1], bins: 0, mean: NaN, peak: NaN, peakHz: NaN, area: 0, above: 0, mainsBins: 0 };
  let sum = 0;
  let mainsPeak = 0;
  // the Hann taper spreads a mains line over two bins each side
  const mainsHalf = Math.max(o.mainsHalfWidthHz, 2 * df + 1e-9);
  for (let k = 1; k <= half; k++) {
    const near = o.mainsHz > 0 && Math.abs(f[k] - o.mainsHz) <= mainsHalf;
    if (near) mainsPeak = Math.max(mainsPeak, coh[k]);
    if (f[k] < o.band[0] || f[k] > o.band[1]) continue;
    if (near) {
      band.mainsBins++;
      continue; // mains sits inside the band: leave it out of the summary
    }
    band.bins++;
    sum += coh[k];
    if (!(coh[k] <= band.peak)) {
      band.peak = coh[k];
      band.peakHz = f[k];
    }
    if (coh[k] > cl95) {
      band.above++;
      band.area += (coh[k] - cl95) * df;
    }
  }
  band.mean = band.bins ? sum / band.bins : NaN;
  if (L > 1 && mainsPeak > Math.max(3 * cl95, 0.1))
    warnings.push(`Strong coherence at ${o.mainsHz} Hz (${mainsPeak.toFixed(2)}): mains pickup shared by both channels. Bins within ${mainsHalf.toFixed(0)} Hz of it are left out of the band summary.`);

  // cumulant density, scaled so that identical signals give 1 at lag 0
  const qr = Float64Array.from(sxyRe);
  const qi = Float64Array.from(sxyIm);
  fft(qr, qi, true);
  let wsum = 0;
  for (let i = 0; i < N; i++) wsum += hann[i] * hann[i];
  const scale = N * (wsum / N) * Math.sqrt(sumSqX * sumSqY) || 1;
  const maxLag = Math.min(half - 1, Math.round((o.maxLagMs / 1000) * fs));
  const lagMs = new Float64Array(2 * maxLag + 1);
  const q = new Float64Array(2 * maxLag + 1);
  let peak = { lagMs: NaN, value: 0 };
  for (let j = -maxLag; j <= maxLag; j++) {
    const v = qr[(j + N) % N] / scale;
    lagMs[j + maxLag] = (1000 * j) / fs;
    q[j + maxLag] = v;
    if (Math.abs(v) > Math.abs(peak.value)) peak = { lagMs: (1000 * j) / fs, value: v };
  }
  const qLimit = L > 0 ? 1.96 / Math.sqrt(L * N) : NaN;

  return {
    fs,
    segLen: N,
    L,
    skipped,
    f,
    coh,
    phase,
    cl95,
    band,
    mainsPeak,
    cumulant: { lagMs, q, peak, limit: qLimit },
    rms: { x: L ? Math.sqrt(sumSqX / (L * N)) : NaN, y: L ? Math.sqrt(sumSqY / (L * N)) : NaN },
    psd: { x: sxx.map((v) => (L ? v / L : 0)), y: syy.map((v) => (L ? v / L : 0)) },
    warnings,
    options: o,
  };
}

// Raw recording ({n, si, v} from store.loadRaw, 6 columns) -> gap-free arrays
// on the sample-index grid for two channels, with a validity mask.
export function rawPair(raw, chX, chY) {
  if (!raw || !raw.n) return null;
  const first = raw.si[0];
  const len = raw.si[raw.n - 1] - first + 1;
  const x = new Float64Array(len);
  const y = new Float64Array(len);
  const valid = new Uint8Array(len);
  for (let i = 0; i < raw.n; i++) {
    const j = raw.si[i] - first;
    x[j] = raw.v[i * 6 + chX];
    y[j] = raw.v[i * 6 + chY];
    valid[j] = 1;
  }
  // hold the last value across gaps so the filter sees no step to zero
  let missing = 0;
  for (let j = 1; j < len; j++)
    if (!valid[j]) {
      x[j] = x[j - 1];
      y[j] = y[j - 1];
      missing++;
    }
  return { x, y, valid, first, missing };
}

// Time windows (seconds on the recording axis) for a gait phase, from the
// strides of the gait analysis ({hs, to, hsNext} in seconds).
export function phaseWindows(strides, phase) {
  const out = [];
  for (const s of strides || []) {
    if (!(s.hsNext > s.hs)) continue;
    if (phase === 'swing' && s.to > s.hs && s.hsNext > s.to) out.push([s.to, s.hsNext]);
    else if (phase === 'stance' && s.to > s.hs) out.push([s.hs, s.to]);
    else if (phase === 'stride') out.push([s.hs, s.hsNext]);
  }
  return out;
}

// One call for the app: raw recording + meta.raw + windows on the recording
// time axis -> coherence result (or {error}).
export function analyzeRawCoherence(raw, rawMeta, chX, chY, { windows = null, ...opts } = {}) {
  const pair = rawPair(raw, chX, chY);
  if (!pair) return { error: 'This recording has no raw 2 kHz EMG.' };
  const fs = rawMeta.hz;
  const tFirst = rawMeta.t0 + pair.first / fs; // recording time of pair.x[0]
  const rel = windows ? windows.map(([a, b]) => [a - tFirst, b - tFirst]) : null;
  if (pair.x.length < (opts.segLen || COH_DEFAULTS.segLen)) return { error: 'The raw EMG is shorter than one segment.' };
  const res = coherence(pair.x, pair.y, fs, { ...opts, windows: rel, valid: pair.missing ? pair.valid : null });
  res.windows = windows ? windows.length : 0;
  res.missing = pair.missing;
  return res;
}
