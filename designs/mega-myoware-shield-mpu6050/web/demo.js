// A software stand-in for the Mega sketch: same commands, same binary frames,
// synthetic signals. Lets the app be tried (and tested) with no hardware.
import { encodeData, encodeText, popcount, TYPE_INFO } from './protocol.js';
import { makeScenario } from './gaitsim.js';

// One leg: IMU A on the shank, IMU B on the foot: stand 3 s, walk 12 strides, repeat.
const WALK = makeScenario({ standS: 3, strides: 12, T: 1.1, jitter: 0.04, sl: 1.2, seed: 11, limb: 'shank-foot' });

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
        this.setRate(this.rate);
      } else if (cmd[0] === 'x') this.streaming = false;
      else if (cmd[0] === 'r') this.setRate(arg);
      else if (cmd[0] === 'e') {
        this.emgMask = (arg || 0) & 0x3f;
        this.setRate(this.rate);
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
      this.seq = (this.seq + 1) & 0xffff;
      this.us = (this.us + period) % 2 ** 32;
      if (Math.random() < this.dropRate) continue;
      parts.push(encodeData(s));
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
    // the other jacks echo them at lower gain.
    const emg = [];
    for (let ch = 0; ch < 6; ch++) {
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

  async close() {
    clearInterval(this.timer);
    this.timer = null;
    this.streaming = false;
  }
}
