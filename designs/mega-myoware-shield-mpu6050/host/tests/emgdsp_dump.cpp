// Host harness for firmware/esp32_standalone_stream/emgdsp.h.
// stdin: mode (0 avg, 1 arv), then 12-bit ADC samples at 2 kHz.
// stdout: one frame value (0..1023 counts) per 8 samples, as the firmware sends at 250 Hz.
#include <cstdio>
#include "../../firmware/esp32_standalone_stream/emgdsp.h"

int main() {
  int mode = 0;
  if (scanf("%d", &mode) != 1) return 1;
  emgdsp::Proc proc = mode == 1 ? emgdsp::PROC_ARV : emgdsp::PROC_AVG;
  emgdsp::Channel ch;
  ch.reset();
  int raw, k = 0;
  while (scanf("%d", &raw) == 1) {
    ch.add((uint16_t)raw, proc);
    if (++k == 8) {
      printf("%u\n", emgdsp::toCounts(ch.take(), proc));
      k = 0;
    }
  }
  return 0;
}
