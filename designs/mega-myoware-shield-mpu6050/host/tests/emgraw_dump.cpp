// Host harness for firmware/esp32_standalone_stream/emgraw.h.
// Pushes 300 samples (value = 100 * channel + sample index mod 100) through
// the ring the way the firmware does, draining at uneven times, once letting
// it overrun, and prints every 'E' frame as hex, one per line.
// argv[1]: EMG mask (default 3).
#include <cstdio>
#include <cstdlib>
#include "../../firmware/esp32_standalone_stream/emgraw.h"

static emgraw::Ring ring;
static emgraw::Row out[emgraw::RING_ROWS];

static void drain(uint8_t mask, uint32_t tUs) {
  uint32_t idx0 = 0;
  uint16_t n = ring.drain(out, emgraw::RING_ROWS, idx0);
  uint8_t per = emgraw::maxRows(mask);
  static uint8_t buf[255 + frame::OVERHEAD];
  for (uint16_t at = 0; at < n; at += per) {
    uint8_t k = (uint8_t)((n - at) < per ? (n - at) : per);
    size_t len = emgraw::buildFrame(buf, idx0 + at, tUs, mask, out + at, k);
    for (size_t i = 0; i < len; i++) printf("%02x", buf[i]);
    printf("\n");
  }
}

int main(int argc, char** argv) {
  uint8_t mask = argc > 1 ? (uint8_t)atoi(argv[1]) : 3;
  ring.reset();
  for (uint32_t i = 0; i < 300; i++) {
    uint16_t raw[frame::MAX_EMG];
    for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) raw[ch] = (uint16_t)(100 * ch + i % 100);
    ring.push(raw);
    // drain after samples 7, 15, 23 (regular frames), then stall until 199
    // (the 128-row ring overruns), then regular again
    if (i == 7 || i == 15 || i == 23 || i == 199 || (i > 199 && i % 8 == 7)) drain(mask, 4294967000u + i * 500u);
  }
  drain(mask, 4294967000u + 300u * 500u);
  fprintf(stderr, "%u\n", (unsigned)ring.overruns);
  return 0;
}
