// Arduino Mega 2560 + MyoWare 2.0 Arduino Shield + up to two MPU-6050 (GY-521)
// + ZS-040 (HC-05 / HC-06) Bluetooth + optional ESP32 Wi-Fi bridge. Streams
// EMG and IMU samples to the web app in ../../web over USB, Bluetooth or Wi-Fi.
//
// Pins
//   MyoWare shield jacks  A0..A5 (the shield routes jack n to An)
//   MPU-6050 SDA / SCL    20 / 21 (the shield's SDA / SCL pins are the same bus)
//   IMU A                 AD0 to GND (or floating) -> address 0x68
//   IMU B                 AD0 to 3.3 V / 5 V       -> address 0x69
//   ZS-040                Serial1 (18 TX, 19 RX) or Serial3 (14 TX, 15 RX)
//   ESP32 Wi-Fi bridge    Serial2 (16 TX2 -> divider -> ESP32 GPIO16,
//                         17 RX2 <- ESP32 GPIO17), see ../esp32_wifi_bridge
//   The sketch listens on all ports and streams to whichever port sends it a
//   command.
//
// Commands (ASCII, one per line, on USB or Bluetooth)
//   ?        send an info frame
//   s        start binary streaming on this port (what the web app uses)
//   p        start CSV text streaming on this port (for Serial Monitor)
//   x        stop streaming
//   r<hz>    set the sample rate, clamped to what the link can carry
//   e<mask>  choose EMG channels, bit n = An (e1 = A0 only, e63 = all six)
//   i        rescan the IMUs
#include <Wire.h>
#include "frame.h"

#define FW_VERSION "mega-myoware-1.2"

// The ZS-040 ships at 9600 baud. After raising it with ../hc05_setup
// (AT+UART=115200,0,0), change this to 115200 for much higher sample rates.
#ifndef BT_BAUD
#define BT_BAUD 9600UL
#endif
// Serial2 talks to the ESP32 Wi-Fi bridge. 500000 is exact on a 16 MHz Mega
// (921600 would be 8 % off) and carries every sample rate the sketch allows.
#ifndef WIFI_BAUD
#define WIFI_BAUD 500000UL
#endif
#define USB_BAUD 115200UL
#define MAX_RATE_HZ 500
#define DEFAULT_EMG_MASK 0x01

const uint8_t MPU_ADDR[frame::MAX_IMU] = {0x68, 0x69};
// ±8 g and ±500 °/s; the web app reads these scales from the info frame.
// (1.0 used ±4 g, which a sensor at the ankle can exceed in swing.)
const uint16_t ACCEL_LSB_PER_G = 4096;
const char GYRO_LSB_PER_DPS[] = "65.5";

struct Port {
  HardwareSerial* serial;
  const char* name;
  uint32_t baud;
  char line[16];
  uint8_t len;
};

Port ports[] = {
  {&Serial, "USB", USB_BAUD, {0}, 0},
  {&Serial1, "Serial1", BT_BAUD, {0}, 0},
  {&Serial2, "Serial2", WIFI_BAUD, {0}, 0},
  {&Serial3, "Serial3", BT_BAUD, {0}, 0},
};
const uint8_t PORT_COUNT = sizeof(ports) / sizeof(ports[0]);

enum Mode : uint8_t { MODE_IDLE, MODE_BINARY, MODE_CSV };

Mode mode = MODE_IDLE;
Port* out = nullptr;
uint8_t emgMask = DEFAULT_EMG_MASK;
uint8_t imuMask = 0;
uint8_t imuWhoAmI[frame::MAX_IMU] = {0, 0};
uint16_t rateHz = 0;  // 0 until a port is chosen
uint32_t periodUs = 0;
uint32_t nextUs = 0;
uint16_t seq = 0;
uint32_t sent = 0;
uint32_t dropped = 0;
uint32_t lastImuRetryMs = 0;
uint32_t lastBlinkMs = 0;

// ---------- MPU-6050 ----------

bool mpuWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

int mpuRead8(uint8_t addr, uint8_t reg) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(addr, (uint8_t)1) != 1) return -1;
  return Wire.read();
}

bool mpuInit(uint8_t slot) {
  uint8_t addr = MPU_ADDR[slot];
  int who = mpuRead8(addr, 0x75);
  // Genuine parts answer 0x68; common clones answer 0x70, 0x72 or 0x98.
  if (who <= 0 || who == 0xFF) return false;
  imuWhoAmI[slot] = (uint8_t)who;
  return mpuWrite(addr, 0x6B, 0x80) &&   // reset
         (delay(100), true) &&
         mpuWrite(addr, 0x6B, 0x01) &&   // wake, PLL on gyro X
         mpuWrite(addr, 0x19, 0x00) &&   // sample rate divider: 1 kHz internal
         mpuWrite(addr, 0x1A, 0x03) &&   // DLPF 44 Hz accel / 42 Hz gyro
         mpuWrite(addr, 0x1B, 0x08) &&   // gyro ±500 °/s
         mpuWrite(addr, 0x1C, 0x10);     // accel ±8 g
}

void scanImus() {
  imuMask = 0;
  for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
    imuWhoAmI[k] = 0;
    if (mpuInit(k)) imuMask |= 1 << k;
  }
}

bool mpuReadMotion(uint8_t slot, int16_t* v) {
  uint8_t addr = MPU_ADDR[slot];
  Wire.beginTransmission(addr);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, (uint8_t)14) != 14) return false;
  uint8_t b[14];
  for (uint8_t i = 0; i < 14; i++) b[i] = Wire.read();
  // Skip the temperature word at bytes 6..7.
  const uint8_t at[6] = {0, 2, 4, 8, 10, 12};
  for (uint8_t a = 0; a < 6; a++) v[a] = (int16_t)((b[at[a]] << 8) | b[at[a] + 1]);
  return true;
}

// ---------- rate and output ----------

uint16_t bytesPerSample() {
  if (mode == MODE_CSV)  // worst-case text line
    return 14 + 6 * frame::popcount(emgMask) + 42 * frame::popcount(imuMask);
  return frame::OVERHEAD + frame::dataPayloadLen(emgMask, imuMask);
}

uint16_t maxRateFor(const Port* p) {
  if (!p) p = &ports[0];
  // 10 bits per byte on the wire, keep 15 % headroom.
  uint32_t hz = (p->baud / 10UL) * 85UL / 100UL / bytesPerSample();
  if (hz > MAX_RATE_HZ) hz = MAX_RATE_HZ;
  if (hz < 1) hz = 1;
  return (uint16_t)hz;
}

void setRate(uint16_t hz) {
  uint16_t maxHz = maxRateFor(out);
  if (hz == 0 || hz > maxHz) hz = maxHz;
  rateHz = hz;
  periodUs = 1000000UL / hz;
}

void sendFrame(Port* p, uint8_t type, const char* text) {
  uint8_t buf[255 + frame::OVERHEAD];
  size_t n = strlen(text);
  if (n > 255) n = 255;
  size_t len = frame::wrap(buf, type, (const uint8_t*)text, (uint8_t)n);
  p->serial->write(buf, len);
}

void sendInfo(Port* p) {
  char json[240];
  snprintf(json, sizeof(json),
           "{\"fw\":\"%s\",\"port\":\"%s\",\"baud\":%lu,\"rate\":%u,\"max_rate\":%u,"
           "\"emg_mask\":%u,\"imu_mask\":%u,\"who\":[%u,%u],\"accel_lsb_per_g\":%u,"
           "\"gyro_lsb_per_dps\":%s,\"adc_ref_v\":5.0,\"sent\":%lu,\"dropped\":%lu}",
           FW_VERSION, p->name, (unsigned long)p->baud, rateHz, maxRateFor(p), emgMask, imuMask,
           imuWhoAmI[0], imuWhoAmI[1], ACCEL_LSB_PER_G, GYRO_LSB_PER_DPS,
           (unsigned long)sent, (unsigned long)dropped);
  if (mode == MODE_CSV) {
    p->serial->print(F("# "));
    p->serial->println(json);
  } else {
    sendFrame(p, frame::TYPE_INFO, json);
  }
}

void printCsvHeader(Port* p) {
  p->serial->print(F("# seq,t_ms"));
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
    if (emgMask & (1 << ch)) { p->serial->print(F(",A")); p->serial->print(ch); }
  const char* axes[6] = {"ax", "ay", "az", "gx", "gy", "gz"};
  for (uint8_t k = 0; k < frame::MAX_IMU; k++)
    if (imuMask & (1 << k))
      for (uint8_t a = 0; a < 6; a++) {
        p->serial->print(k == 0 ? F(",A_") : F(",B_"));
        p->serial->print(axes[a]);
      }
  p->serial->println();
}

void startStream(Port* p, Mode m) {
  out = p;
  mode = m;
  seq = 0;
  sent = 0;
  dropped = 0;
  setRate(rateHz);
  sendInfo(p);
  if (m == MODE_CSV) printCsvHeader(p);
  nextUs = micros() + 1000;
}

// ---------- commands ----------

void handleCommand(Port* p, const char* cmd) {
  switch (cmd[0]) {
    case '?':
      sendInfo(p);
      break;
    case 's':
      startStream(p, MODE_BINARY);
      break;
    case 'p':
      startStream(p, MODE_CSV);
      break;
    case 'x':
      mode = MODE_IDLE;
      sendInfo(p);
      break;
    case 'r':
      if (!out) out = p;
      setRate((uint16_t)atoi(cmd + 1));
      sendInfo(p);
      break;
    case 'e': {
      int m = atoi(cmd + 1) & 0x3F;
      emgMask = (uint8_t)m;
      if (!out) out = p;
      setRate(rateHz);  // re-clamp: more channels means bigger frames
      sendInfo(p);
      if (mode == MODE_CSV) printCsvHeader(p);
      break;
    }
    case 'i':
      scanImus();
      if (!out) out = p;
      setRate(rateHz);
      sendInfo(p);
      break;
    default:
      if (mode != MODE_BINARY) {
        p->serial->print(F("# unknown command: "));
        p->serial->println(cmd);
      }
  }
}

void pollPort(Port* p) {
  while (p->serial->available()) {
    char c = (char)p->serial->read();
    if (c == '\n' || c == '\r') {
      if (p->len) {
        p->line[p->len] = 0;
        handleCommand(p, p->line);
        p->len = 0;
      }
    } else if (p->len < sizeof(p->line) - 1) {
      p->line[p->len++] = c;
    }
  }
}

// ---------- sampling ----------

void takeSample(frame::Sample& s) {
  s.seq = seq;
  s.tUs = micros();
  s.emgMask = emgMask;
  s.imuMask = imuMask;
  s.flags = 0;
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
    s.emg[ch] = (emgMask & (1 << ch)) ? (uint16_t)analogRead(A0 + ch) : 0;
  for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
    if (!(imuMask & (1 << k))) continue;
    if (!mpuReadMotion(k, s.imu[k])) {
      for (uint8_t a = 0; a < 6; a++) s.imu[k][a] = 0;
      s.flags |= 1 << k;
    }
  }
}

void emitCsv(Port* p, const frame::Sample& s) {
  HardwareSerial* o = p->serial;
  o->print(s.seq);
  o->print(',');
  o->print(s.tUs / 1000UL);
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
    if (s.emgMask & (1 << ch)) { o->print(','); o->print(s.emg[ch]); }
  for (uint8_t k = 0; k < frame::MAX_IMU; k++)
    if (s.imuMask & (1 << k))
      for (uint8_t a = 0; a < 6; a++) { o->print(','); o->print(s.imu[k][a]); }
  o->println();
}

void emitBinary(Port* p, const frame::Sample& s) {
  uint8_t buf[frame::OVERHEAD + frame::DATA_HEADER + 2 * frame::MAX_EMG + 12 * frame::MAX_IMU];
  size_t len = frame::buildData(buf, s);
  // Never block the sampler: if the link has fallen behind, skip this frame.
  // The web app sees the gap in seq.
  if ((size_t)p->serial->availableForWrite() < len) {
    dropped++;
    return;
  }
  p->serial->write(buf, len);
  sent++;
}

void setup() {
  for (uint8_t i = 0; i < PORT_COUNT; i++) ports[i].serial->begin(ports[i].baud);
  pinMode(LED_BUILTIN, OUTPUT);
  Wire.begin();
  Wire.setClock(400000);
  Wire.setWireTimeout(3000, true);
  scanImus();
  for (uint8_t i = 0; i < PORT_COUNT; i++) {
    ports[i].serial->print(F("# " FW_VERSION " ready. imu_mask="));
    ports[i].serial->print(imuMask);
    ports[i].serial->println(F(". Send p for CSV, s for binary, ? for info."));
  }
}

void loop() {
  for (uint8_t i = 0; i < PORT_COUNT; i++) pollPort(&ports[i]);

  uint32_t nowMs = millis();
  if (mode == MODE_IDLE) {
    digitalWrite(LED_BUILTIN, LOW);
    return;
  }
  if (nowMs - lastBlinkMs >= 250) {
    lastBlinkMs = nowMs;
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }

  uint32_t now = micros();
  if ((int32_t)(now - nextUs) < 0) return;
  // If we fell more than a few periods behind (e.g. a stuck I2C read), skip
  // ahead and advance seq by the missed periods so the gap stays visible.
  uint32_t late = now - nextUs;
  if (late > 4 * periodUs) {
    uint32_t missed = late / periodUs;
    seq += (uint16_t)missed;
    dropped += missed;
    nextUs += missed * periodUs;
  }
  nextUs += periodUs;

  frame::Sample s;
  takeSample(s);
  if (mode == MODE_BINARY) emitBinary(out, s);
  else emitCsv(out, s);
  seq++;

  // A loose IMU wire: retry the missing sensors once a second.
  if ((s.flags || imuMask != 0x03) && nowMs - lastImuRetryMs > 1000) {
    lastImuRetryMs = nowMs;
    for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
      bool missing = !(imuMask & (1 << k));
      bool failed = s.flags & (1 << k);
      if (failed && !mpuInit(k)) continue;
      if (missing && mpuInit(k)) {
        imuMask |= 1 << k;
        setRate(rateHz);
        if (mode == MODE_BINARY) sendInfo(out);
      }
    }
  }
}
