// Unprocessed 2 kHz EMG for the ESP32 streamer (firmware 1.3, command w1).
//
// The 250 Hz data frames carry one summary value per EMG channel (emgdsp.h).
// That is enough for envelopes, but not for anything that needs the EMG
// waveform itself: coherence between two electrode sites, median frequency,
// noise-floor and aliasing checks. With raw streaming on, every ADC sample is
// also kept in a small ring and sent, untouched, in 'E' frames:
//
//   A5 5A | 'E' | len | payload[len] | crc8        (same framing as frame.h)
//
//   u32 idx0   index of the first sample in this frame. The index counts ADC
//              ticks since raw streaming was switched on, so a jump between
//              frames means samples were lost (ring overrun or link loss).
//   u32 t_us   micros() when the ring was drained: the board time just after
//              the newest sample that was in the ring. Same clock as t_us in
//              the 'D' frames, so the app can place the samples on the IMU
//              timeline.
//   u8  mask   bit n set -> channel An present (A0..A5)
//   u8  n      samples in this frame
//   u16 v[n][popcount(mask)]   12-bit ADC counts, sample by sample
//
// Pure C++ (no Arduino calls) so the host test can run it.
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "frame.h"

namespace emgraw {

const uint8_t TYPE_RAW = 'E';
const uint8_t HEADER = 10;
const uint16_t RING_ROWS = 128;  // 64 ms at 2 kHz

struct Row {
  uint16_t v[frame::MAX_EMG];
};

// Most samples one frame can hold (payload is at most 255 bytes).
inline uint8_t maxRows(uint8_t mask) {
  uint8_t pc = frame::popcount(mask);
  if (!pc) return 0;
  return (uint8_t)((255 - HEADER) / (2 * pc));
}

// Single writer (the ADC timer) and single reader (the stream loop); the
// caller guards both with the same lock.
struct Ring {
  Row rows[RING_ROWS];
  uint16_t tail = 0;      // oldest stored row
  uint16_t count = 0;
  uint32_t tailIdx = 0;   // sample index of the oldest stored row
  uint32_t nextIdx = 0;   // sample index the next push gets
  uint32_t overruns = 0;  // samples overwritten before they were sent

  void reset() {
    tail = 0;
    count = 0;
    tailIdx = 0;
    nextIdx = 0;
    overruns = 0;
  }

  // raw: one value per channel A0..A5 (unused channels are ignored later).
  void push(const uint16_t* raw) {
    if (count == RING_ROWS) {  // full: drop the oldest, the index shows the gap
      tail = (uint16_t)((tail + 1) % RING_ROWS);
      tailIdx++;
      count--;
      overruns++;
    }
    Row& r = rows[(tail + count) % RING_ROWS];
    for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) r.v[ch] = raw[ch];
    count++;
    nextIdx++;
  }

  // Moves up to max rows to out (oldest first). Returns how many, and the
  // sample index of the first one in idx0.
  uint16_t drain(Row* out, uint16_t max, uint32_t& idx0) {
    uint16_t n = count < max ? count : max;
    idx0 = tailIdx;
    for (uint16_t i = 0; i < n; i++) out[i] = rows[(tail + i) % RING_ROWS];
    tail = (uint16_t)((tail + n) % RING_ROWS);
    tailIdx += n;
    count = (uint16_t)(count - n);
    return n;
  }
};

// Packs n rows (n <= maxRows(mask)) as a complete 'E' frame at out, which
// needs 255 + frame::OVERHEAD bytes. Returns the frame length.
inline size_t buildFrame(uint8_t* out, uint32_t idx0, uint32_t tUs, uint8_t mask, const Row* rows, uint8_t n) {
  uint8_t payload[255];
  uint8_t* p = payload;
  p = frame::put32(p, idx0);
  p = frame::put32(p, tUs);
  *p++ = mask;
  *p++ = n;
  for (uint8_t i = 0; i < n; i++)
    for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
      if (mask & (1 << ch)) p = frame::put16(p, rows[i].v[ch]);
  return frame::wrap(out, TYPE_RAW, payload, (uint8_t)(p - payload));
}

}  // namespace emgraw
