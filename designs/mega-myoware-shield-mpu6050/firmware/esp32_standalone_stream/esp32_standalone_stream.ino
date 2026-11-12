// ESP32 Standalone Streamer for AFO Gait Analysis.
// Directly samples MyoWare 2.0 EMG and up to two MPU-6050 IMUs.
// Gait layout (web app "One leg: shank + foot"): IMU A on the shank just
// above the outer ankle bone, IMU B on top of the foot (midfoot / laces).
//
// 1.1 (2026-11-10): fixes the duplicated scanBus() header that stopped the
// 8 Nov sketch compiling; gyro range ±1000 °/s (was ±500) so the foot sensor
// does not clip in swing. The app reads the scale from the info frame.
// 1.2 (2026-11-12): EMG is sampled at 2 kHz on its own timer, not once per
// 250 Hz frame, so the MyoWare RAW output no longer aliases. Each frame
// carries the mean of the 8 samples (ENV, "g0", default) or, for RAW ("g1"),
// the average rectified value after a 20-450 Hz band-pass (see emgdsp.h).
// Streams data over WebSocket (ws://afo-mega.local/ws) and USB Serial to the web app.
//
// Wiring:
//   MyoWare Shield A0 (Jack 1) -> ESP32 GPIO 34 (ADC1_CH6)
//   MyoWare Shield A1 (Jack 2) -> ESP32 GPIO 35 (ADC1_CH7) [optional]
//   MyoWare Shield 3.3V        -> ESP32 3V3
//   MyoWare Shield GND         -> ESP32 GND
//   IMU A (Bus 0):
//     VCC -> ESP32 3V3, GND -> ESP32 GND
//     SDA -> ESP32 GPIO 21, SCL -> ESP32 GPIO 22
//     AD0 -> GND or disconnected (address 0x68)
//   IMU B (Bus 1):
//     VCC -> ESP32 3V3, GND -> ESP32 GND
//     SDA -> ESP32 GPIO 18, SCL -> ESP32 GPIO 19
//     AD0 -> GND or 3V3 (address 0x68 or 0x69 auto-detected)
//
// Wi-Fi:
//   Access Point: AFO-MEGA, password: afo-mega-1, IP: 192.168.4.1
//   Or save your home Wi-Fi via USB Serial console at 115200:
//     ssid YourNetwork
//     pass YourPassword
//     restart

#include <Arduino.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <esp_http_server.h>
#include <Wire.h>
#include <esp_timer.h>
#include "frame.h"
#include "emgdsp.h"

#define FW_VERSION "esp32-stream-1.2"
#define PIN_I2C0_SDA 21
#define PIN_I2C0_SCL 22
#define PIN_I2C1_SDA 18
#define PIN_I2C1_SCL 19
#define DEFAULT_RATE_HZ 250
#define MAX_RATE_HZ 500
#define DEFAULT_EMG_MASK 0x01
#define HOSTNAME "afo-mega"
#define AP_SSID "AFO-MEGA"
#define AP_PASS "afo-mega-1"
#define JOIN_TIMEOUT_MS 15000
#define BATCH_BYTES 512
#define BATCH_MS 8

const uint8_t EMG_PINS[frame::MAX_EMG] = {34, 35, 32, 33, 36, 39};
TwoWire* imuBus[frame::MAX_IMU] = {nullptr, nullptr};
uint8_t imuAddr[frame::MAX_IMU] = {0x68, 0x68};
const uint16_t ACCEL_LSB_PER_G = 4096;
const char GYRO_LSB_PER_DPS[] = "32.8";  // ±1000 °/s: a foot in swing can pass 500 °/s

enum Mode : uint8_t { MODE_IDLE, MODE_BINARY, MODE_CSV };

Preferences prefs;
httpd_handle_t server = nullptr;
volatile int wsFd = -1;

Mode mode = MODE_IDLE;
uint8_t emgMask = DEFAULT_EMG_MASK;
uint8_t imuMask = 0;
uint8_t imuWhoAmI[frame::MAX_IMU] = {0, 0};
uint16_t rateHz = DEFAULT_RATE_HZ;
uint32_t periodUs = 1000000UL / DEFAULT_RATE_HZ;
uint32_t nextUs = 0;
uint16_t seq = 0;
uint32_t sent = 0;
uint32_t dropped = 0;
uint32_t framesSent = 0;
uint32_t sendErrors = 0;
uint32_t clients = 0;

// EMG at 2 kHz (emgdsp.h). The timer task fills emgCh; loopTask takes one
// value per channel per frame under emgMux.
emgdsp::Channel emgCh[frame::MAX_EMG];
emgdsp::Proc emgProc = emgdsp::PROC_AVG;
portMUX_TYPE emgMux = portMUX_INITIALIZER_UNLOCKED;
esp_timer_handle_t emgTimer = nullptr;
volatile uint16_t emgLastRaw = 0;  // channel 0, for the status page

String netInfo;
char usbLine[96];
uint8_t usbLen = 0;

// ---------- Thread-Safe Command Queue ----------

#define CMD_QUEUE_LEN 16
static char cmdQueue[CMD_QUEUE_LEN][32];
static volatile uint8_t cmdHead = 0;
static volatile uint8_t cmdTail = 0;

void queueCommand(const char* c) {
  uint8_t next = (cmdHead + 1) % CMD_QUEUE_LEN;
  if (next != cmdTail) {
    strncpy(cmdQueue[cmdHead], c, sizeof(cmdQueue[0]) - 1);
    cmdQueue[cmdHead][sizeof(cmdQueue[0]) - 1] = 0;
    cmdHead = next;
  }
}

bool dequeueCommand(char* out) {
  if (cmdHead == cmdTail) return false;
  strcpy(out, cmdQueue[cmdTail]);
  cmdTail = (cmdTail + 1) % CMD_QUEUE_LEN;
  return true;
}

// ---------- MPU-6050 ----------

bool mpuWrite(TwoWire& bus, uint8_t addr, uint8_t reg, uint8_t val) {
  bus.beginTransmission(addr);
  bus.write(reg);
  bus.write(val);
  return bus.endTransmission() == 0;
}

int mpuRead8(TwoWire& bus, uint8_t addr, uint8_t reg) {
  bus.beginTransmission(addr);
  bus.write(reg);
  if (bus.endTransmission(false) != 0) return -1;
  if (bus.requestFrom((int)addr, 1) != 1) return -1;
  return bus.read();
}

bool mpuInit(TwoWire& bus, uint8_t addr, uint8_t& whoOut) {
  int who = mpuRead8(bus, addr, 0x75);
  if (who <= 0 || who == 0xFF) return false;
  whoOut = (uint8_t)who;
  return mpuWrite(bus, addr, 0x6B, 0x80) &&   // reset
         (delay(50), true) &&
         mpuWrite(bus, addr, 0x6B, 0x01) &&   // wake, PLL on gyro X
         mpuWrite(bus, addr, 0x19, 0x00) &&   // sample rate divider: 1 kHz internal
         mpuWrite(bus, addr, 0x1A, 0x03) &&   // DLPF 44 Hz accel / 42 Hz gyro
         mpuWrite(bus, addr, 0x1B, 0x10) &&   // gyro ±1000 °/s (foot swing exceeds ±500)
         mpuWrite(bus, addr, 0x1C, 0x10);     // accel ±8 g
}

bool mpuReadMotion(TwoWire& bus, uint8_t addr, int16_t* v) {
  bus.beginTransmission(addr);
  bus.write(0x3B);
  if (bus.endTransmission(false) != 0) return false;
  if (bus.requestFrom((int)addr, 14) != 14) return false;
  uint8_t b[14];
  for (uint8_t i = 0; i < 14; i++) b[i] = bus.read();
  const uint8_t at[6] = {0, 2, 4, 8, 10, 12};
  for (uint8_t a = 0; a < 6; a++) v[a] = (int16_t)((b[at[a]] << 8) | b[at[a] + 1]);
  return true;
}

void scanBus(TwoWire& bus, const char* name, int sda, int scl) {
  Serial.printf("# --- Scanning %s (SDA=%d, SCL=%d) ---\n", name, sda, scl);
  uint8_t found = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    bus.beginTransmission(addr);
    if (bus.endTransmission() == 0) {
      Serial.printf("# %s: device detected at 0x%02X\n", name, addr);
      found++;
    }
  }
  if (!found) Serial.printf("# %s: no devices found\n", name);
}

void scanImus() {
  imuMask = 0;
  for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
    imuBus[k] = nullptr;
    imuAddr[k] = 0;
    imuWhoAmI[k] = 0;
  }

  scanBus(Wire, "Bus 0 [IMU A]", PIN_I2C0_SDA, PIN_I2C0_SCL);
  scanBus(Wire1, "Bus 1 [IMU B]", PIN_I2C1_SDA, PIN_I2C1_SCL);

  // Probe Bus 0 for IMU A (checks 0x68, then 0x69)
  uint8_t who = 0;
  if (mpuInit(Wire, 0x68, who)) {
    imuBus[0] = &Wire;
    imuAddr[0] = 0x68;
    imuWhoAmI[0] = who;
    imuMask |= 1;
  } else if (mpuInit(Wire, 0x69, who)) {
    imuBus[0] = &Wire;
    imuAddr[0] = 0x69;
    imuWhoAmI[0] = who;
    imuMask |= 1;
  }

  // Probe Bus 1 for IMU B (checks 0x68, then 0x69)
  who = 0;
  if (mpuInit(Wire1, 0x68, who)) {
    imuBus[1] = &Wire1;
    imuAddr[1] = 0x68;
    imuWhoAmI[1] = who;
    imuMask |= 2;
  } else if (mpuInit(Wire1, 0x69, who)) {
    imuBus[1] = &Wire1;
    imuAddr[1] = 0x69;
    imuWhoAmI[1] = who;
    imuMask |= 2;
  }

  // Fallback: If Bus 1 was empty but Bus 0 has a second sensor on 0x69
  if (!(imuMask & 2) && imuAddr[0] == 0x68) {
    who = 0;
    if (mpuInit(Wire, 0x69, who)) {
      imuBus[1] = &Wire;
      imuAddr[1] = 0x69;
      imuWhoAmI[1] = who;
      imuMask |= 2;
    }
  }

  Serial.printf("# IMU scan result: mask=%u (IMU A: %s [0x%02X on %s], IMU B: %s [0x%02X on %s])\n",
                imuMask,
                (imuMask & 1) ? "OK" : "missing", imuWhoAmI[0], (imuBus[0] == &Wire ? "Bus0" : "none"),
                (imuMask & 2) ? "OK" : "missing", imuWhoAmI[1], (imuBus[1] == &Wire1 ? "Bus1" : imuBus[1] == &Wire ? "Bus0" : "none"));
}

// ---------- sampling ----------

static void emgTick(void*) {
  uint8_t mask = emgMask;
  uint16_t raw[frame::MAX_EMG];
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
    if (mask & (1 << ch)) raw[ch] = (uint16_t)analogRead(EMG_PINS[ch]);
  if (mask & 1) emgLastRaw = raw[0];
  portENTER_CRITICAL(&emgMux);
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++)
    if (mask & (1 << ch)) emgCh[ch].add(raw[ch], emgProc);
  portEXIT_CRITICAL(&emgMux);
}

void setEmg(uint8_t mask, emgdsp::Proc proc) {
  portENTER_CRITICAL(&emgMux);
  emgMask = mask;
  emgProc = proc;
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) emgCh[ch].reset();
  portEXIT_CRITICAL(&emgMux);
}

void startEmgTimer() {
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) {
    analogSetPinAttenuation(EMG_PINS[ch], ADC_11db);
    emgCh[ch].reset();
  }
  analogReadResolution(12);
  esp_timer_create_args_t args = {};
  args.callback = emgTick;
  args.name = "emg2k";
  if (esp_timer_create(&args, &emgTimer) == ESP_OK) esp_timer_start_periodic(emgTimer, emgdsp::TICK_US);
}

void setRate(uint16_t hz) {
  if (hz == 0 || hz > MAX_RATE_HZ) hz = MAX_RATE_HZ;
  rateHz = hz;
  periodUs = 1000000UL / hz;
}

void takeSample(frame::Sample& s) {
  s.seq = seq;
  s.tUs = micros();
  s.emgMask = emgMask;
  s.imuMask = imuMask;
  s.flags = 0;
  float v[frame::MAX_EMG];
  portENTER_CRITICAL(&emgMux);
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) v[ch] = (emgMask & (1 << ch)) ? emgCh[ch].take() : 0;
  emgdsp::Proc proc = emgProc;
  portEXIT_CRITICAL(&emgMux);
  // 0..1023 counts; the volts per 1023 counts are in the info frame (adc_ref_v).
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) s.emg[ch] = (emgMask & (1 << ch)) ? emgdsp::toCounts(v[ch], proc) : 0;
  for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
    if (!(imuMask & (1 << k)) || !imuBus[k]) continue;
    if (!mpuReadMotion(*imuBus[k], imuAddr[k], s.imu[k])) {
      for (uint8_t a = 0; a < 6; a++) s.imu[k][a] = 0;
      s.flags |= (1 << k);
    }
  }
}

// ---------- WebSocket output batching ----------

static uint8_t wsBatch[2048];
static size_t wsBatchLen = 0;
static uint32_t wsBatchFirstAt = 0;

void flushWs() {
  if (wsBatchLen == 0 || wsFd < 0 || !server) {
    wsBatchLen = 0;
    return;
  }
  httpd_ws_frame_t f = {};
  f.type = HTTPD_WS_TYPE_BINARY;
  f.payload = wsBatch;
  f.len = wsBatchLen;
  if (httpd_ws_send_data(server, wsFd, &f) == ESP_OK) {
    framesSent++;
  } else {
    sendErrors++;
  }
  wsBatchLen = 0;
}

void queueWs(const uint8_t* data, size_t len) {
  if (wsFd < 0 || !server) {
    wsBatchLen = 0;
    return;
  }
  if (wsBatchLen + len > sizeof(wsBatch)) flushWs();
  if (wsBatchLen == 0) wsBatchFirstAt = millis();
  memcpy(wsBatch + wsBatchLen, data, len);
  wsBatchLen += len;
  if (wsBatchLen >= BATCH_BYTES || (millis() - wsBatchFirstAt >= BATCH_MS)) {
    flushWs();
  }
}

void sendInfo() {
  char json[320];
  // emg_hz: ADC rate per EMG channel; emg_proc: avg (ENV) or arv (RAW, rectified on the board).
  int n = snprintf(json, sizeof(json),
           "{\"fw\":\"%s\",\"port\":\"%s\",\"baud\":%lu,\"rate\":%u,\"max_rate\":%u,"
           "\"emg_mask\":%u,\"imu_mask\":%u,\"who\":[%u,%u],\"accel_lsb_per_g\":%u,"
           "\"gyro_lsb_per_dps\":%s,\"adc_ref_v\":%s,\"emg_hz\":%lu,\"emg_proc\":\"%s\","
           "\"sent\":%lu,\"dropped\":%lu}",
           FW_VERSION, "Wi-Fi", 115200UL, rateHz, MAX_RATE_HZ, emgMask, imuMask,
           imuWhoAmI[0], imuWhoAmI[1], ACCEL_LSB_PER_G, GYRO_LSB_PER_DPS,
           emgdsp::refVolts(emgProc), (unsigned long)emgdsp::FS_HZ, emgdsp::name(emgProc),
           (unsigned long)sent, (unsigned long)dropped);
  if (n < 0 || n > 255) {  // a frame payload is at most 255 bytes: drop the counters
    char* tail = strstr(json, ",\"sent\"");
    if (tail) strcpy(tail, "}");
  }

  uint8_t buf[256 + frame::OVERHEAD];
  size_t len = frame::wrap(buf, frame::TYPE_INFO, (const uint8_t*)json, (uint8_t)strlen(json));

  if (wsFd >= 0 && server) {
    flushWs();
    httpd_ws_frame_t f = {};
    f.type = HTTPD_WS_TYPE_BINARY;
    f.payload = buf;
    f.len = len;
    if (httpd_ws_send_data(server, wsFd, &f) == ESP_OK) {
      framesSent++;
    } else {
      sendErrors++;
    }
  }

  // Also send over USB serial
  Serial.write(buf, len);
}

void emitBinary(const frame::Sample& s) {
  uint8_t buf[frame::OVERHEAD + frame::DATA_HEADER + 2 * frame::MAX_EMG + 12 * frame::MAX_IMU];
  size_t len = frame::buildData(buf, s);

  if (wsFd >= 0) queueWs(buf, len);
  if (Serial.availableForWrite() >= (int)len) Serial.write(buf, len);

  sent++;
}

void emitCsv(const frame::Sample& s) {
  Serial.print(s.seq);
  Serial.print(',');
  Serial.print(s.tUs / 1000UL);
  for (uint8_t ch = 0; ch < frame::MAX_EMG; ch++) {
    if (s.emgMask & (1 << ch)) {
      Serial.print(',');
      Serial.print(s.emg[ch]);
    }
  }
  for (uint8_t k = 0; k < frame::MAX_IMU; k++) {
    if (s.imuMask & (1 << k)) {
      for (uint8_t a = 0; a < 6; a++) {
        Serial.print(',');
        Serial.print(s.imu[k][a]);
      }
    }
  }
  Serial.println();
}

// ---------- Command Handling (Runs safely in loopTask) ----------

void handleCommand(const char* cmd) {
  switch (cmd[0]) {
    case '?':
      sendInfo();
      break;
    case 's':
      mode = MODE_BINARY;
      sent = 0;
      dropped = 0;
      sendInfo();
      nextUs = micros() + 1000;
      break;
    case 'p':
      mode = MODE_CSV;
      sent = 0;
      dropped = 0;
      sendInfo();
      nextUs = micros() + 1000;
      break;
    case 'x':
      mode = MODE_IDLE;
      flushWs();
      break;
    case 'r': {
      int hz = atoi(cmd + 1);
      if (hz > 0) setRate((uint16_t)hz);
      sendInfo();
      break;
    }
    case 'e': {
      int m = atoi(cmd + 1);
      if (m >= 0 && m < (1 << frame::MAX_EMG)) setEmg((uint8_t)m, emgProc);
      sendInfo();
      break;
    }
    case 'g':  // g0: ENV output (mean), g1: RAW output (band-pass, rectify, mean)
      setEmg(emgMask, atoi(cmd + 1) == 1 ? emgdsp::PROC_ARV : emgdsp::PROC_AVG);
      sendInfo();
      break;
    case 'i':
      scanImus();
      sendInfo();
      break;
  }
}

// ---------- Web Server ----------

static void onSocketClose(httpd_handle_t, int fd) {
  if (fd == wsFd) {
    wsFd = -1;
    mode = MODE_IDLE;
    Serial.printf("app disconnected (socket %d)\n", fd);
  }
  close(fd);
}

static esp_err_t wsHandler(httpd_req_t* req) {
  int fd = httpd_req_to_sockfd(req);
  if (fd >= 0 && fd != wsFd) {
    int old = wsFd;
    wsFd = fd;
    clients++;
    if (old >= 0 && old != fd) httpd_sess_trigger_close(server, old);
    Serial.printf("app connected (socket %d)\n", fd);
  }
  if (req->method == HTTP_GET) return ESP_OK;

  httpd_ws_frame_t f = {};
  esp_err_t r = httpd_ws_recv_frame(req, &f, 0);
  if (r != ESP_OK) return r;
  if (f.len == 0) return ESP_OK;
  if (f.len > 128) return ESP_FAIL;

  uint8_t buf[128];
  f.payload = buf;
  r = httpd_ws_recv_frame(req, &f, f.len);
  if (r != ESP_OK) return r;

  if (f.type == HTTPD_WS_TYPE_TEXT || f.type == HTTPD_WS_TYPE_BINARY) {
    buf[f.len] = 0;
    char* line = (char*)buf;
    while (*line) {
      char* end = strpbrk(line, "\r\n");
      if (end) *end = 0;
      if (strlen(line) > 0) queueCommand(line);
      if (!end) break;
      line = end + 1;
    }
  }
  return ESP_OK;
}

static esp_err_t statusHandler(httpd_req_t* req) {
  String html = F("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                  "<title>AFO ESP32 Streamer</title><body style='font:15px system-ui;margin:24px;max-width:40em'>"
                  "<h1 style='font-size:20px'>AFO Gait ESP32 Streamer</h1><p>");
  html += F(FW_VERSION "<br>");
  html += netInfo;
  html += F("</p><p>Web app: <b>http://localhost:8000</b></p><pre>");
  html += "Mode: " + String(mode == MODE_BINARY ? "STREAMING BINARY" : mode == MODE_CSV ? "CSV" : "IDLE") + "\n";
  html += "EMG A0 live (12-bit, 2 kHz): " + String(emgLastRaw) + ", mode " + String(emgdsp::name(emgProc)) + "\n";
  html += "IMU Mask: " + String(imuMask) + " (IMU A 0x68: " + String(imuMask & 1 ? "FOUND" : "not found") +
          ", IMU B 0x69: " + String(imuMask & 2 ? "FOUND" : "not found") + ")\n";
  html += "Rate: " + String(rateHz) + " Hz\n";
  html += "App connected: " + String(wsFd >= 0 ? "YES" : "no") + "\n";
  html += "Frames sent: " + String(framesSent) + "\n";
  html += "Send errors: " + String(sendErrors) + "\n";
  html += "</pre>";
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, html.c_str(), html.length());
}

static void startServer() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.close_fn = onSocketClose;
  cfg.lru_purge_enable = true;
  if (httpd_start(&server, &cfg) != ESP_OK) {
    Serial.println("HTTP server failed to start");
    return;
  }
  httpd_uri_t ws = {};
  ws.uri = "/ws";
  ws.method = HTTP_GET;
  ws.handler = wsHandler;
  ws.is_websocket = true;
  httpd_register_uri_handler(server, &ws);

  httpd_uri_t root = {};
  root.uri = "/";
  root.method = HTTP_GET;
  root.handler = statusHandler;
  httpd_register_uri_handler(server, &root);
}

// ---------- Wi-Fi ----------

static void startWifi() {
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  WiFi.setHostname(HOSTNAME);
  if (ssid.length()) {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.begin(ssid.c_str(), pass.c_str());
    Serial.printf("joining %s", ssid.c_str());
    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < JOIN_TIMEOUT_MS) {
      delay(250);
      Serial.print('.');
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
      netInfo = "On Wi-Fi " + ssid + " at <b>" + WiFi.localIP().toString() + "</b> (" HOSTNAME ".local)";
      Serial.printf("joined %s: http://%s/ (or http://" HOSTNAME ".local/)\n", ssid.c_str(), WiFi.localIP().toString().c_str());
      return;
    }
    Serial.println("could not join; making its own network instead");
    WiFi.disconnect(true);
  }
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  netInfo = "Own network " AP_SSID " (password " AP_PASS ") at <b>" + WiFi.softAPIP().toString() + "</b>";
  Serial.printf("own network %s, password %s, address %s\n", AP_SSID, AP_PASS, WiFi.softAPIP().toString().c_str());
}

// ---------- USB Console ----------

static void pollUsb() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      usbLine[usbLen] = 0;
      if (usbLen) {
        String s(usbLine);
        s.trim();
        if (s.startsWith("ssid ")) {
          prefs.putString("ssid", s.substring(5));
          Serial.println("saved network name; now pass <password>, then restart");
        } else if (s.startsWith("pass ")) {
          prefs.putString("pass", s.substring(5));
          Serial.println("saved password; type restart");
        } else if (s == "forget") {
          prefs.remove("ssid");
          prefs.remove("pass");
          Serial.println("forgot network; type restart");
        } else if (s == "restart") {
          ESP.restart();
        } else if (s == "status") {
          Serial.printf(FW_VERSION "\n%s\nApp connected: %s, mode: %d, frames: %lu, errors: %lu, imuMask: %d\n",
                        netInfo.c_str(), wsFd >= 0 ? "yes" : "no", (int)mode,
                        (unsigned long)framesSent, (unsigned long)sendErrors, imuMask);
        } else {
          queueCommand(usbLine);
        }
      }
      usbLen = 0;
    } else if (usbLen < sizeof(usbLine) - 1) {
      usbLine[usbLen++] = c;
    }
  }
}

// ---------- Setup & Loop ----------

void setup() {
  Serial.begin(115200);
  delay(100);

  // ADC 0-3.3 V on all six EMG pins, sampled at 2 kHz by its own timer
  startEmgTimer();

  // Initialize I2C Bus 0 (IMU A) on GPIO 21 / 22
  Wire.begin(PIN_I2C0_SDA, PIN_I2C0_SCL);
  Wire.setClock(100000);
  Wire.setTimeOut(25);

  // Initialize I2C Bus 1 (IMU B) on GPIO 18 / 19
  Wire1.begin(PIN_I2C1_SDA, PIN_I2C1_SCL);
  Wire1.setClock(100000);
  Wire1.setTimeOut(25);

  scanImus();

  prefs.begin("wifi", false);
  startWifi();
  if (MDNS.begin(HOSTNAME)) MDNS.addService("http", "tcp", 80);
  startServer();

  Serial.printf("# %s ready. imu_mask=%u (IMU A: %s, IMU B: %s)\n",
                FW_VERSION, imuMask, (imuMask & 1) ? "OK" : "missing", (imuMask & 2) ? "OK" : "missing");
}

void loop() {
  pollUsb();

  // Process queued commands safely on loopTask
  char cmd[32];
  while (dequeueCommand(cmd)) {
    handleCommand(cmd);
  }

  if (mode == MODE_BINARY || mode == MODE_CSV) {
    uint32_t now = micros();
    if ((int32_t)(now - nextUs) >= 0) {
      nextUs += periodUs;
      if ((int32_t)(now - nextUs) >= 0) {
        nextUs = now + periodUs;
      }
      frame::Sample s;
      takeSample(s);
      seq++;
      if (mode == MODE_BINARY) emitBinary(s);
      else emitCsv(s);
    }
  }

  if (wsBatchLen > 0 && (millis() - wsBatchFirstAt >= BATCH_MS)) {
    flushWs();
  }

  delay(1);
}
