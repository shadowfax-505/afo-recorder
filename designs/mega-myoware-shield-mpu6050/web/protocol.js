// Frame format: see ../firmware/mega_myoware_stream/frame.h
//   A5 5A | type | len | payload[len] | crc8 (poly 0x07 over type, len, payload)

export const SYNC0 = 0xa5;
export const SYNC1 = 0x5a;
export const TYPE_DATA = 0x44; // 'D'
export const TYPE_INFO = 0x49; // 'I'
export const TYPE_LOG = 0x4c; // 'L'
export const MAX_EMG = 6;
export const MAX_IMU = 2;
export const IMU_AXES = ['ax', 'ay', 'az', 'gx', 'gy', 'gz'];
export const IMU_NAMES = ['IMU A (0x68)', 'IMU B (0x69)'];

export function crc8(bytes, start = 0, end = bytes.length, crc = 0) {
  for (let i = start; i < end; i++) {
    crc ^= bytes[i];
    for (let b = 0; b < 8; b++) crc = crc & 0x80 ? ((crc << 1) ^ 0x07) & 0xff : (crc << 1) & 0xff;
  }
  return crc;
}

export function popcount(v) {
  let n = 0;
  for (; v; v >>= 1) n += v & 1;
  return n;
}

export function wrap(type, payload) {
  const out = new Uint8Array(payload.length + 5);
  out[0] = SYNC0;
  out[1] = SYNC1;
  out[2] = type;
  out[3] = payload.length;
  out.set(payload, 4);
  out[4 + payload.length] = crc8(out, 2, 4 + payload.length);
  return out;
}

// sample: {seq, tUs, emgMask, imuMask, flags, emg[6], imu[2][6]}
export function encodeData(s) {
  const n = 9 + 2 * popcount(s.emgMask) + 12 * popcount(s.imuMask);
  const p = new DataView(new ArrayBuffer(n));
  let o = 0;
  p.setUint16(o, s.seq & 0xffff, true); o += 2;
  p.setUint32(o, s.tUs >>> 0, true); o += 4;
  p.setUint8(o++, s.emgMask);
  p.setUint8(o++, s.imuMask);
  p.setUint8(o++, s.flags || 0);
  for (let ch = 0; ch < MAX_EMG; ch++) if (s.emgMask & (1 << ch)) { p.setUint16(o, s.emg[ch], true); o += 2; }
  for (let k = 0; k < MAX_IMU; k++)
    if (s.imuMask & (1 << k)) for (let a = 0; a < 6; a++) { p.setInt16(o, s.imu[k][a], true); o += 2; }
  return wrap(TYPE_DATA, new Uint8Array(p.buffer));
}

export function encodeText(type, text) {
  return wrap(type, new TextEncoder().encode(text).slice(0, 255));
}

export function decodeData(payload) {
  if (payload.length < 9) return null;
  const p = new DataView(payload.buffer, payload.byteOffset, payload.byteLength);
  const s = {
    seq: p.getUint16(0, true),
    tUs: p.getUint32(2, true),
    emgMask: p.getUint8(6),
    imuMask: p.getUint8(7),
    flags: p.getUint8(8),
    emg: new Array(MAX_EMG).fill(null),
    imu: [null, null],
  };
  if (payload.length !== 9 + 2 * popcount(s.emgMask) + 12 * popcount(s.imuMask)) return null;
  let o = 9;
  for (let ch = 0; ch < MAX_EMG; ch++) if (s.emgMask & (1 << ch)) { s.emg[ch] = p.getUint16(o, true); o += 2; }
  for (let k = 0; k < MAX_IMU; k++) {
    if (!(s.imuMask & (1 << k))) continue;
    const v = [];
    for (let a = 0; a < 6; a++) { v.push(p.getInt16(o, true)); o += 2; }
    s.imu[k] = v;
  }
  return s;
}

// Splits a byte stream into frames. Bytes outside frames are collected as
// text lines (the sketch prints "# ..." banners before streaming starts).
export class FrameParser {
  constructor({ onSample, onInfo, onLog, onText } = {}) {
    this.onSample = onSample || (() => {});
    this.onInfo = onInfo || (() => {});
    this.onLog = onLog || (() => {});
    this.onText = onText || (() => {});
    this.buf = new Uint8Array(4096);
    this.len = 0;
    this.text = '';
    this.stats = { frames: 0, crcErrors: 0, badFrames: 0 };
  }

  push(bytes) {
    if (this.len + bytes.length > this.buf.length) {
      const next = new Uint8Array(Math.max(this.buf.length * 2, this.len + bytes.length));
      next.set(this.buf.subarray(0, this.len));
      this.buf = next;
    }
    this.buf.set(bytes, this.len);
    this.len += bytes.length;
    this._drain();
  }

  _drain() {
    const b = this.buf;
    let i = 0;
    while (i < this.len) {
      if (b[i] !== SYNC0) {
        this._textByte(b[i]);
        i++;
        continue;
      }
      if (i + 1 >= this.len) break;
      if (b[i + 1] !== SYNC1) {
        this._textByte(b[i]);
        i++;
        continue;
      }
      if (i + 4 > this.len) break;
      const type = b[i + 2];
      const n = b[i + 3];
      if (i + 5 + n > this.len) break;
      if (crc8(b, i + 2, i + 4 + n) !== b[i + 4 + n]) {
        this.stats.crcErrors++;
        i++; // resync on the next A5
        continue;
      }
      const payload = b.slice(i + 4, i + 4 + n);
      i += 5 + n;
      this.stats.frames++;
      this._dispatch(type, payload);
    }
    b.copyWithin(0, i, this.len);
    this.len -= i;
  }

  _dispatch(type, payload) {
    if (type === TYPE_DATA) {
      const s = decodeData(payload);
      if (s) this.onSample(s);
      else this.stats.badFrames++;
    } else if (type === TYPE_INFO) {
      const text = new TextDecoder().decode(payload);
      try {
        this.onInfo(JSON.parse(text));
      } catch {
        this.stats.badFrames++;
      }
    } else if (type === TYPE_LOG) {
      this.onLog(new TextDecoder().decode(payload));
    } else {
      this.stats.badFrames++;
    }
  }

  _textByte(c) {
    if (c === 10 || c === 13) {
      const line = this.text.trim();
      this.text = '';
      if (line.startsWith('#')) this.onText(line);
    } else if (c >= 32 && c < 127 && this.text.length < 300) {
      this.text += String.fromCharCode(c);
    } else {
      this.text = ''; // binary noise, not a banner
    }
  }
}

// Turns wrapping 16-bit seq and 32-bit microsecond stamps into continuous
// counters, and counts samples the link skipped.
export class SampleClock {
  constructor() {
    this.reset();
  }

  reset() {
    this.lastSeq = null;
    this.seqBase = 0;
    this.lastUs = null;
    this.usBase = 0;
    this.lost = 0;
    this.received = 0;
  }

  // Returns {seq, us} unwrapped. A seq that jumps backwards by a lot means the
  // board restarted streaming, which starts a fresh timeline.
  step(s) {
    if (this.lastSeq !== null) {
      let d = (s.seq - this.lastSeq) & 0xffff;
      // Duplicate or backwards jump (streaming restarted): keep counting forward.
      if (d === 0 || d > 0x8000) d = 1;
      this.seqBase += d;
      if (d > 1) this.lost += d - 1;
      const du = (s.tUs - this.lastUs) >>> 0;
      this.usBase += du;
    }
    this.lastSeq = s.seq;
    this.lastUs = s.tUs;
    this.received++;
    return { seq: this.seqBase, us: this.usBase };
  }
}

export function scalesFromInfo(info) {
  return {
    accelLsbPerG: (info && info.accel_lsb_per_g) || 8192,
    gyroLsbPerDps: (info && info.gyro_lsb_per_dps) || 65.5,
    adcRefV: (info && info.adc_ref_v) || 5.0,
  };
}
