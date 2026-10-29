// Binary frame format shared by the Mega sketch, the host test and the web app.
//
//   A5 5A | type | len | payload[len] | crc8
//
// crc8 is CRC-8/SMBUS (poly 0x07, init 0x00) over type, len and payload.
// All multi-byte fields are little-endian.
//
// type 'D' (sample), payload:
//   u16 seq        increments once per sample period, gaps mean skipped samples
//   u32 t_us       micros() at the start of the sample (wraps every ~71.6 min)
//   u8  emg_mask   bit n set -> analog channel An follows (A0..A5)
//   u8  imu_mask   bit0 -> IMU A (0x68) follows, bit1 -> IMU B (0x69) follows
//   u8  flags      bit0/bit1 -> IMU A/B read failed this sample (values are 0)
//   u16 emg[popcount(emg_mask)]           ADC counts 0..1023
//   i16 imu[popcount(imu_mask)][6]        ax ay az gx gy gz, raw LSB
//
// type 'I' (info), payload: ASCII JSON describing the current configuration.
// type 'L' (log), payload: ASCII text for the status line.
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace frame {

const uint8_t SYNC0 = 0xA5;
const uint8_t SYNC1 = 0x5A;
const uint8_t TYPE_DATA = 'D';
const uint8_t TYPE_INFO = 'I';
const uint8_t TYPE_LOG = 'L';
const uint8_t MAX_EMG = 6;
const uint8_t MAX_IMU = 2;
const uint8_t OVERHEAD = 5;  // sync x2, type, len, crc
const uint8_t DATA_HEADER = 9;

struct Sample {
  uint16_t seq;
  uint32_t tUs;
  uint8_t emgMask;
  uint8_t imuMask;
  uint8_t flags;
  uint16_t emg[MAX_EMG];      // indexed by analog channel
  int16_t imu[MAX_IMU][6];    // indexed by IMU slot
};

inline uint8_t crc8(uint8_t crc, uint8_t b) {
  crc ^= b;
  for (uint8_t i = 0; i < 8; i++) crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x07) : (uint8_t)(crc << 1);
  return crc;
}

inline uint8_t popcount(uint8_t v) {
  uint8_t n = 0;
  while (v) { n += v & 1; v >>= 1; }
  return n;
}

inline uint8_t dataPayloadLen(uint8_t emgMask, uint8_t imuMask) {
  return DATA_HEADER + 2 * popcount(emgMask) + 12 * popcount(imuMask);
}

// Wraps payload into a frame at out; out needs len + OVERHEAD bytes.
inline size_t wrap(uint8_t* out, uint8_t type, const uint8_t* payload, uint8_t len) {
  out[0] = SYNC0;
  out[1] = SYNC1;
  out[2] = type;
  out[3] = len;
  uint8_t crc = crc8(crc8(0, type), len);
  for (uint8_t i = 0; i < len; i++) {
    out[4 + i] = payload[i];
    crc = crc8(crc, payload[i]);
  }
  out[4 + len] = crc;
  return (size_t)len + OVERHEAD;
}

inline uint8_t* put16(uint8_t* p, uint16_t v) { p[0] = v & 0xFF; p[1] = v >> 8; return p + 2; }
inline uint8_t* put32(uint8_t* p, uint32_t v) {
  p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; p[2] = (v >> 16) & 0xFF; p[3] = v >> 24;
  return p + 4;
}

// Packs a sample as a complete 'D' frame. Returns the frame length.
inline size_t buildData(uint8_t* out, const Sample& s) {
  uint8_t payload[DATA_HEADER + 2 * MAX_EMG + 12 * MAX_IMU];
  uint8_t* p = payload;
  p = put16(p, s.seq);
  p = put32(p, s.tUs);
  *p++ = s.emgMask;
  *p++ = s.imuMask;
  *p++ = s.flags;
  for (uint8_t ch = 0; ch < MAX_EMG; ch++)
    if (s.emgMask & (1 << ch)) p = put16(p, s.emg[ch]);
  for (uint8_t k = 0; k < MAX_IMU; k++)
    if (s.imuMask & (1 << k))
      for (uint8_t a = 0; a < 6; a++) p = put16(p, (uint16_t)s.imu[k][a]);
  return wrap(out, TYPE_DATA, payload, (uint8_t)(p - payload));
}

}  // namespace frame
