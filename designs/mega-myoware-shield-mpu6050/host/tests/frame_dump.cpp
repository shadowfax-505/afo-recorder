// Prints frames built by the firmware's frame.h as hex, one per line, so
// protocol.test.mjs can check the web app decodes exactly what the Mega sends.
#include <cstdio>
#include <cstring>
#include "../../firmware/mega_myoware_stream/frame.h"

static void dump(const uint8_t* b, size_t n) {
  for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
  printf("\n");
}

int main() {
  uint8_t buf[300];
  const uint8_t masks[][2] = {{0x01, 0x03}, {0x3F, 0x03}, {0x00, 0x01}, {0x05, 0x02}, {0x01, 0x00}, {0x3F, 0x00}};
  for (unsigned m = 0; m < sizeof(masks) / sizeof(masks[0]); m++) {
    frame::Sample s;
    memset(&s, 0, sizeof(s));
    s.seq = (uint16_t)(65530 + m * 3);
    s.tUs = 4294967000u + m * 250u;
    s.emgMask = masks[m][0];
    s.imuMask = masks[m][1];
    s.flags = (uint8_t)(m & 3);
    for (int ch = 0; ch < 6; ch++) s.emg[ch] = (uint16_t)(ch * 200 + m);
    for (int k = 0; k < 2; k++)
      for (int a = 0; a < 6; a++) s.imu[k][a] = (int16_t)((a % 2 ? -1 : 1) * (k * 10000 + a * 1111 + m));
    dump(buf, frame::buildData(buf, s));
  }
  const char* info = "{\"fw\":\"test\",\"rate\":20}";
  dump(buf, frame::wrap(buf, frame::TYPE_INFO, (const uint8_t*)info, (uint8_t)strlen(info)));
  return 0;
}
