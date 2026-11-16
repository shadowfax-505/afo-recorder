// A software stand-in for the Mega sketch: same commands, same binary frames,
// synthetic signals. Lets the app be tried (and tested) with no hardware.
import { encodeData, encodeRaw, encodeText, popcount, TYPE_INFO } from './protocol.js';
import { makeScenario } from './gaitsim.js';

// One leg: IMU A on the shank, IMU B on the foot: stand 3 s, walk 12 strides, repeat.
const WALK = makeScenario({ standS: 3, strides: 12, T: 1.1, jitter: 0.04, sl: 1.2, seed: 11, limb: 'shank-foot' });

// Raw 2 kHz EMG for the demo (command w1, like ESP32 firmware 1.3): noise
// around mid-scale whose size follows the muscle bursts. Jacks A0 and A2 stand
// for two sites on the same muscle (same burst timing) and share a 20-30 Hz
// rhythm in their amplitude, so the coherence panel has something to find;
// the other jacks are independent.
const RAW_HZ = 2000;
const DRIVE = [20.5, 22, 23.5, 25, 26.5, 28, 29.5].map((f, i) => ({ w: 2 * Math.PI * f, p: 1.7 * i * i }));
const gauss = () => Math.sqrt(-2 * Math.log(Math.random() + 1e-12)) * Math.cos(2 * Math.PI * Math.random());
function rawEmgAt(t, tw, ch) {
  if (ch >= 4) return Math.round(280 + 3120 * WALK.switchAt(tw, ch === 4 ? 'heel' : 'toe') + 30 * (Math.random() - 0.5));
  const level = WALK.emgAt(tw, ch % 2) * (1 - Math.floor(ch / 2) * 0.25); // 40 at rest, up to ~600 in a burst
  let m = 1;
  if (ch === 0 || ch === 2) m = Math.max(0, 1 + 0.25 * DRIVE.reduce((a, d) => a + Math.sin(d.w * t + d.p), 0));
  return Math.max(0, Math.min(4095, Math.round(2048 + 0.9 * level * m * gauss())));
}

export class DemoTransport {
  constructor({ baud = 115200, dropRate = 0 } = {}) {
    this.label = 'Demo (synthetic)';
    this.baud = baud;
    this.dropRate = dropRate;
    this.onBytes = () => {};
    this.onClose = () => {};
    this.emgMask = 0x01;
    this.imuMask = 0x03;
    this.rate = 0;
    this.streaming = false;
    this.seq = 0;
    this.us = 0;
    this.timer = null;
    this.carry = 0;
    this.raw = false;
    this.rawIdx = 0;
    this.rawCarry = 0;
    this.proc = 'avg';
    this.fsw = 0;
  }

  maxRate() {
    const bytes = 5 + 9 + 2 * popcount(this.emgMask) + 12 * popcount(this.imuMask);
    return Math.max(1, Math.min(500, Math.floor(((this.baud / 10) * 0.85) / bytes)));
  }

  setRate(hz) {
    const m = this.maxRate();
    this.rate = !hz || hz > m ? m : hz;
  }

  info() {
    return {
      fw: 'demo-synthetic',
      port: 'Demo',
      baud: this.baud,
      rate: this.rate,
      max_rate: this.maxRate(),
      emg_mask: this.emgMask,
      imu_mask: this.imuMask,
      who: [104, 104],
      accel_lsb_per_g: 4096,
      gyro_lsb_per_dps: 65.5,
      adc_ref_v: 5.0,
      emg_hz: RAW_HZ,
      emg_proc: this.proc,
      emg_raw: this.raw ? 1 : 0,
      fsw: this.fsw,
      synthetic: true,
    };
  }

  async open() {
    this.setRate(0);
    // A random spot on the board clock, 1.5 s before the synthetic walk starts.
    this.us = (Math.floor(Math.random() * (1e9 / (WALK.period * 1e6))) * WALK.period + WALK.walkStart - 1.5) * 1e6;
    this.emit(new TextEncoder().encode('# demo-synthetic ready. Send p for CSV, s for binary, ? for info.\n'));
    this.timer = setInterval(() => this.tick(), 20);
  }

  emit(bytes) {
    queueMicrotask(() => this.onBytes(bytes));
  }

  async write(text) {
    for (const cmd of text.split(/[\r\n]+/).filter(Boolean)) {
      const arg = parseInt(cmd.slice(1), 10);
      if (cmd[0] === 's') {
        this.streaming = true;
        this.seq = 0;
        this.rawIdx = 0;
        this.setRate(this.rate);
      } else if (cmd[0] === 'x') this.streaming = false;
      else if (cmd[0] === 'r') this.setRate(arg);
      else if (cmd[0] === 'e') {
        this.emgMask = (arg || 0) & 0x3f;
        this.setRate(this.rate);
      } else if (cmd[0] === 'g') this.proc = arg === 1 ? 'arv' : 'avg';
      else if (cmd[0] === 'f') this.fsw = (arg || 0) & 0x3f;
      else if (cmd[0] === 'w') {
        this.raw = arg === 1;
        this.rawIdx = 0;
      } else if (cmd[0] !== '?' && cmd[0] !== 'i') continue;
      this.emit(encodeText(TYPE_INFO, JSON.stringify(this.info())));
    }
  }

  tick() {
    if (!this.streaming) return;
    this.carry += (this.rate * 20) / 1000;
    const n = Math.floor(this.carry);
    this.carry -= n;
    const period = 1e6 / this.rate;
    const parts = [];
    for (let i = 0; i < n; i++) {
      const s = this.sample();
      const raw = this.raw && this.emgMask ? this.rawFrame(period) : null;
      this.seq = (this.seq + 1) & 0xffff;
      this.us = (this.us + period) % 2 ** 32;
      if (Math.random() < this.dropRate) continue;
      parts.push(encodeData(s));
      if (raw) parts.push(raw);
    }
    if (!parts.length) return;
    const out = new Uint8Array(parts.reduce((a, p) => a + p.length, 0));
    let o = 0;
    for (const p of parts) {
      out.set(p, o);
      o += p.length;
    }
    this.onBytes(out);
  }

  sample() {
    const t = this.us / 1e6;
    const tw = t % WALK.period;
    // A0 = tibialis anterior, A1 = gastrocnemius, timed by the simulated walk;
    // A2 and A3 echo them at lower gain; A4 and A5 are footswitches under the
    // heel and the forefoot (FSR dividers, see gaitsim.js switchAt).
    const emg = [];
    for (let ch = 0; ch < 6; ch++) {
      if (ch >= 4) {
        emg.push(Math.round(70 + 780 * WALK.switchAt(tw, ch === 4 ? 'heel' : 'toe') + 10 * (Math.random() - 0.5)));
        continue;
      }
      const level = WALK.emgAt(tw, ch % 2) * (1 - Math.floor(ch / 2) * 0.25) * (0.9 + 0.2 * Math.random());
      emg.push(Math.max(0, Math.min(1023, Math.round(level + 12 * (Math.random() - 0.5)))));
    }
    const imu = [0, 1].map((k) => {
      const { acc, gyr } = WALK.at(tw, k);
      return [
        ...acc.map((v) => Math.round(4096 * (v + 0.006 * (Math.random() - 0.5)))),
        ...gyr.map((v, a) => Math.round(65.5 * (v + (k ? -1.2 : 0.8) * (a - 1) + 1.0 * (Math.random() - 0.5)))),
      ];
    });
    return { seq: this.seq, tUs: Math.floor(this.us), emgMask: this.emgMask, imuMask: this.imuMask, flags: 0, emg, imu };
  }

  // The raw samples of the frame period that ends at this.us.
  rawFrame(period) {
    this.rawCarry += (RAW_HZ * period) / 1e6;
    const n = Math.floor(this.rawCarry);
    this.rawCarry -= n;
    const rows = [];
    for (let i = 0; i < n; i++) {
      const t = this.us / 1e6 - (n - 1 - i) / RAW_HZ;
      for (let ch = 0; ch < 6; ch++) if (this.emgMask & (1 << ch)) rows.push(rawEmgAt(t, ((t % WALK.period) + WALK.period) % WALK.period, ch));
    }
    const frame = encodeRaw({ idx0: this.rawIdx, tUs: Math.floor(this.us), mask: this.emgMask, rows });
    this.rawIdx = (this.rawIdx + n) >>> 0;
    return frame;
  }

  async close() {
    clearInterval(this.timer);
    this.timer = null;
    this.streaming = false;
  }
}
