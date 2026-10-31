// Synthetic shank IMU signals for the demo and the gait tests: two sensors
// just above the ankles, standing still, walking a set number of strides,
// then standing again. The sagittal angular velocity follows the usual shank
// pattern (dip at toe-off, large mid-swing peak, dip at initial contact) and
// the accelerometer sees gravity plus the ankle's own motion, so stride
// length can be checked against a known value.

const G = 9.80665;
const N = 2000; // phase table resolution

function gauss(p, c, s) {
  let d = Math.abs(p - c);
  d = Math.min(d, 1 - d); // wrap around the cycle
  return Math.exp(-0.5 * (d / s) ** 2);
}

// Sagittal angle table (degrees) over one cycle, phase 0 = initial contact.
function buildTemplate() {
  const tRef = 1.1;
  const w = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const p = i / N;
    w[i] = 360 * gauss(p, 0.8, 0.075) - 160 * gauss(p, 0.62, 0.03) - 140 * gauss(p, 0, 0.025) + 60 * gauss(p, 0.3, 0.12);
  }
  const mean = w.reduce((s, v) => s + v, 0) / N;
  for (let i = 0; i < N; i++) w[i] -= mean;
  // events at the minima of the template
  const minNear = (c, r) => {
    let k = -1;
    let v = Infinity;
    for (let j = Math.round((c - r) * N); j <= Math.round((c + r) * N); j++) {
      const i = ((j % N) + N) % N;
      if (w[i] < v) {
        v = w[i];
        k = j;
      }
    }
    return k / N;
  };
  const pIc = minNear(0, 0.06);
  const pTo = minNear(0.62, 0.06);
  // angle = integral over time at tRef, zero at mid-stance (phase 0.3)
  const th = new Float64Array(N + 1);
  for (let i = 1; i <= N; i++) th[i] = th[i - 1] + (w[i - 1] * tRef) / N;
  const off = th[Math.round(0.3 * N)];
  for (let i = 0; i <= N; i++) th[i] -= off;
  return { th, pIc, pTo, tRef };
}

const TPL = buildTemplate();

function interp(tab, p) {
  const x = (p - Math.floor(p)) * N;
  const i = Math.floor(x);
  return tab[i] + (tab[i + 1] - tab[i]) * (x - i);
}

// Seeded random numbers so tests are repeatable.
export function rng(seed = 1) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

function rotation(r) {
  // random right-handed orthonormal frame: columns are f, u, m in sensor axes
  const v = () => [r() - 0.5, r() - 0.5, r() - 0.5];
  const nrm = (a) => {
    const n = Math.hypot(...a);
    return a.map((x) => x / n);
  };
  const f = nrm(v());
  let u = v();
  const d = f[0] * u[0] + f[1] * u[1] + f[2] * u[2];
  u = nrm(u.map((x, i) => x - d * f[i]));
  const m = [f[1] * u[2] - f[2] * u[1], f[2] * u[0] - f[0] * u[2], f[0] * u[1] - f[1] * u[0]];
  return { f, u, m };
}

// strides: number of strides per leg; T: mean stride time; jitter: relative SD.
export function makeScenario({ standS = 2.5, strides = 12, T = 1.1, jitter = 0, sl = 1.1, seed = 7, mounts = null } = {}) {
  const r = rng(seed);
  const durs = [];
  for (let k = 0; k < strides; k++) durs.push(T * (1 + jitter * 2 * (r() - 0.5) * Math.sqrt(3)));
  const frames = mounts || [rotation(r), rotation(r)];
  const legStart = [standS, standS + 0.5 * durs[0]];
  const segStarts = legStart.map((s0) => {
    const a = [s0];
    for (const d of durs) a.push(a[a.length - 1] + d);
    return a;
  });
  const walkEnd = segStarts[1][strides];
  const period = walkEnd + standS;

  // phase of leg k at time t: 0.3 (mid-stance) while standing
  function phase(t, k) {
    const s = segStarts[k];
    if (t <= s[0]) return { p: 0.3, cyc: 0, rate: 0 };
    if (t >= s[strides]) return { p: 0.3 + strides, cyc: strides, rate: 0 };
    let j = 0;
    while (t >= s[j + 1]) j++;
    return { p: 0.3 + j + (t - s[j]) / durs[j], cyc: j, rate: 1 / durs[j] };
  }

  // ankle position along the walkway: still in stance, minimum-jerk in swing
  function ankleAcc(p, rate) {
    const q = p - Math.floor(p);
    const sw = 1 + TPL.pIc - TPL.pTo; // swing as a fraction of the cycle
    let s = q - TPL.pTo;
    if (s < 0) s += 1;
    if (s > sw || !rate) return [0, 0];
    s /= sw;
    const k2 = (rate / sw) ** 2;
    const ax = sl * (60 * s - 180 * s * s + 120 * s ** 3) * k2;
    const az = 0.025 * (2 * Math.PI) ** 2 * Math.cos(2 * Math.PI * s) * k2;
    return [ax, az];
  }

  // Sensor readings of leg k (0 = IMU A, 1 = IMU B) at time t: acc in g, gyro in °/s.
  function at(t, k) {
    const { p, rate } = phase(t, k);
    const thDeg = interp(TPL.th, p);
    const eps = 1 / N;
    const wDps = rate ? ((interp(TPL.th, p + eps) - interp(TPL.th, p - eps)) / (2 * eps)) * rate : 0;
    const [ax, az] = ankleAcc(p, rate);
    // body-frame specific force: R(-θ) · (a + g·up)
    const th = (thDeg * Math.PI) / 180;
    const c = Math.cos(th);
    const s = Math.sin(th);
    const wf = ax;
    const wu = az + G;
    const bf = (c * wf + s * wu) / G;
    const bu = (-s * wf + c * wu) / G;
    const { f, u, m } = frames[k];
    const acc = [0, 1, 2].map((i) => f[i] * bf + u[i] * bu);
    const gyr = [0, 1, 2].map((i) => m[i] * wDps);
    return { acc, gyr };
  }

  // true event times per leg
  const truth = [0, 1].map((k) => {
    const ic = [];
    const to = [];
    const s = segStarts[k];
    const timeOf = (ph) => {
      const j = Math.floor(ph - 0.3);
      if (j < 0 || j >= strides) return NaN;
      return s[j] + (ph - 0.3 - j) * durs[j];
    };
    for (let c = 0; c <= strides + 1; c++) {
      const a = timeOf(c + TPL.pIc);
      const b = timeOf(c + TPL.pTo);
      if (Number.isFinite(a)) ic.push(a);
      if (Number.isFinite(b)) to.push(b);
    }
    return { ic, to };
  });

  return { at, truth, period, durs, sl, stancePct: 100 * (TPL.pTo - TPL.pIc), walkStart: standS, walkEnd };
}

// Samples a scenario on a grid with sensor noise and gyro offset.
export function simulateWalk({ fs = 100, noise = true, seed = 3, ...scn } = {}) {
  const sc = makeScenario(scn);
  const r = rng(seed);
  const gauss01 = () => Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r());
  const n = Math.floor(sc.period * fs);
  const t = new Float64Array(n);
  const imu = [0, 1].map(() => Array.from({ length: 6 }, () => new Float64Array(n)));
  const bias = [0, 1].map(() => [0, 1, 2].map(() => (noise ? 4 * (r() - 0.5) : 0)));
  for (let i = 0; i < n; i++) {
    t[i] = i / fs;
    for (let k = 0; k < 2; k++) {
      const { acc, gyr } = sc.at(t[i], k);
      for (let a = 0; a < 3; a++) {
        imu[k][a][i] = acc[a] + (noise ? 0.008 * gauss01() : 0);
        imu[k][3 + a][i] = gyr[a] + bias[k][a] + (noise ? 0.6 * gauss01() : 0);
      }
    }
  }
  return { t, imu, ...sc };
}
