// ESP32 DevKitC Wi-Fi bridge for the Arduino Mega recorder.
//
// Passes bytes both ways between a WebSocket (ws://afo-mega.local/ws) and the
// Mega's Serial2, so the web app in ../../web can stream over Wi-Fi exactly as
// it does over USB or Bluetooth. The Mega sketch (mega_myoware_stream 1.2 or
// later) runs Serial2 at 500000 baud for this.
//
// Wiring (3 signal wires plus power):
//   Mega 16 (TX2) -> 1 kOhm -> ESP32 GPIO16 (RX2), with 2 kOhm from GPIO16 to GND
//                    (the Mega sends 5 V; the ESP32 takes 3.3 V)
//   Mega 17 (RX2) <- ESP32 GPIO17 (TX2), direct
//   Mega GND      -- ESP32 GND
//   5 V (XL6009)  -> ESP32 5V pin (peaks ~250 mA on Wi-Fi). Not at the same
//                    time as the ESP32's own USB cable.
// On a DevKitC with an ESP32-WROVER module GPIO16/17 belong to the PSRAM; use
// MEGA_RX_PIN 25 / MEGA_TX_PIN 26 there instead.
//
// Wi-Fi
//   With no network saved it makes its own network: AFO-MEGA, password
//   afo-mega-1, address 192.168.4.1. Join it from the computer and connect the
//   app to 192.168.4.1 (or afo-mega.local).
//   To join your own Wi-Fi instead, open the ESP32's USB port at 115200
//   (Arduino Serial Monitor, newline on) and type:
//     ssid YourNetwork
//     pass YourPassword
//     restart
//   It prints its IP address when it joins; afo-mega.local also works on macOS.
//   "forget" goes back to its own network, "status" shows counters.
//
// Board: "ESP32 Dev Module" (esp32 core 3.x). No extra libraries.
#include <WiFi.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <esp_http_server.h>
#include <lwip/sockets.h>

#define BRIDGE_VERSION "esp32-wifi-bridge-1.0"
#ifndef MEGA_RX_PIN
#define MEGA_RX_PIN 16
#endif
#ifndef MEGA_TX_PIN
#define MEGA_TX_PIN 17
#endif
#define MEGA_BAUD 500000UL
#define HOSTNAME "afo-mega"
#define AP_SSID "AFO-MEGA"
#define AP_PASS "afo-mega-1"
#define JOIN_TIMEOUT_MS 15000
#define BATCH_BYTES 512   // send to the browser once this much is waiting
#define BATCH_MS 8        // or once the oldest byte has waited this long

HardwareSerial& mega = Serial2;
Preferences prefs;
httpd_handle_t server = nullptr;
volatile int wsFd = -1;
uint32_t toMega = 0, fromMega = 0, framesSent = 0, sendErrors = 0, clients = 0;
String netInfo;
char usbLine[96];
uint8_t usbLen = 0;

// ---------- WebSocket ----------

static void stopMega() { mega.write((const uint8_t*)"x\n", 2); }

static esp_err_t wsHandler(httpd_req_t* req) {
  if (req->method == HTTP_GET) {  // handshake done: this is the new client
    int fd = httpd_req_to_sockfd(req);
    int old = wsFd;
    wsFd = fd;
    clients++;
    if (old >= 0 && old != fd) httpd_sess_trigger_close(server, old);  // newest wins
    Serial.printf("app connected (socket %d)\n", fd);
    return ESP_OK;
  }
  httpd_ws_frame_t f = {};
  esp_err_t r = httpd_ws_recv_frame(req, &f, 0);
  if (r != ESP_OK) return r;
  if (f.len == 0) return ESP_OK;
  if (f.len > 512) return ESP_FAIL;  // commands are a few bytes
  uint8_t buf[512];
  f.payload = buf;
  r = httpd_ws_recv_frame(req, &f, f.len);
  if (r != ESP_OK) return r;
  if (f.type == HTTPD_WS_TYPE_BINARY || f.type == HTTPD_WS_TYPE_TEXT) {
    mega.write(buf, f.len);
    toMega += f.len;
  }
  return ESP_OK;
}

static void onSocketClose(httpd_handle_t, int fd) {
  if (fd == wsFd) {
    wsFd = -1;
    stopMega();  // nobody is listening any more
    Serial.printf("app disconnected (socket %d)\n", fd);
  }
  close(fd);
}

static esp_err_t statusHandler(httpd_req_t* req) {
  String html = F("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                  "<title>AFO Mega Wi-Fi bridge</title><body style='font:15px system-ui;margin:24px;max-width:40em'>"
                  "<h1 style='font-size:20px'>AFO Mega Wi-Fi bridge</h1><p>");
  html += F(BRIDGE_VERSION "<br>");
  html += netInfo;
  html += F("</p><p>In the recorder web app, type this device's address in the ESP32 box and press <b>Connect Wi-Fi</b>. "
            "Open the app from http://localhost on your computer: browsers block this link from an https page.</p><pre>");
  html += "app connected: " + String(wsFd >= 0 ? "yes" : "no") + "\nbytes to Mega: " + String(toMega) +
          "\nbytes from Mega: " + String(fromMega) + "\nframes sent: " + String(framesSent) +
          "\nsend errors: " + String(sendErrors) + "\n</pre>";
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

// Mega -> browser, batched so a 245 Hz stream is ~30 WebSocket frames a second.
static void pumpMega() {
  static uint8_t buf[2048];
  static size_t n = 0;
  static uint32_t firstAt = 0;
  while (mega.available() && n < sizeof(buf)) {
    if (n == 0) firstAt = millis();
    buf[n++] = (uint8_t)mega.read();
  }
  if (!n) return;
  if (n < BATCH_BYTES && millis() - firstAt < BATCH_MS) return;
  fromMega += n;
  int fd = wsFd;
  if (fd >= 0 && server) {
    httpd_ws_frame_t f = {};
    f.type = HTTPD_WS_TYPE_BINARY;
    f.payload = buf;
    f.len = n;
    if (httpd_ws_send_data(server, fd, &f) == ESP_OK)
      framesSent++;
    else
      sendErrors++;
  }
  n = 0;  // with no app connected, bytes are dropped
}

// ---------- Wi-Fi ----------

static void startWifi() {
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  WiFi.setHostname(HOSTNAME);
  if (ssid.length()) {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);  // lower latency
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
    Serial.println("could not join; making its own network instead (type forget to stop trying)");
    WiFi.disconnect(true);
  }
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  netInfo = "Own network " AP_SSID " (password " AP_PASS ") at <b>" + WiFi.softAPIP().toString() + "</b>";
  Serial.printf("own network %s, password %s, address %s\n", AP_SSID, AP_PASS, WiFi.softAPIP().toString().c_str());
}

// ---------- USB console ----------

static void usbCommand(char* line) {
  String s(line);
  s.trim();
  if (s.startsWith("ssid ")) {
    prefs.putString("ssid", s.substring(5));
    Serial.println("saved network name; now pass <password>, then restart");
  } else if (s.startsWith("pass ")) {
    prefs.putString("pass", s.substring(5));
    Serial.println("saved password; type restart");
  } else if (s == "pass") {
    prefs.putString("pass", "");
    Serial.println("open network (no password); type restart");
  } else if (s == "forget") {
    prefs.remove("ssid");
    prefs.remove("pass");
    Serial.println("forgot the network; type restart to use its own AFO-MEGA network");
  } else if (s == "restart") {
    ESP.restart();
  } else if (s == "status" || s == "?") {
    Serial.printf(BRIDGE_VERSION "\n%s\napp connected: %s, to Mega %lu B, from Mega %lu B, frames %lu, send errors %lu, connections %lu\n",
                  netInfo.c_str(), wsFd >= 0 ? "yes" : "no", (unsigned long)toMega, (unsigned long)fromMega,
                  (unsigned long)framesSent, (unsigned long)sendErrors, (unsigned long)clients);
  } else if (s.length()) {
    Serial.println("commands: ssid <name>, pass <password>, restart, forget, status");
  }
}

static void pollUsb() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      usbLine[usbLen] = 0;
      if (usbLen) usbCommand(usbLine);
      usbLen = 0;
    } else if (usbLen < sizeof(usbLine) - 1) {
      usbLine[usbLen++] = c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  mega.setRxBufferSize(8192);
  mega.begin(MEGA_BAUD, SERIAL_8N1, MEGA_RX_PIN, MEGA_TX_PIN);
  delay(200);
  Serial.println("\n# " BRIDGE_VERSION);
  prefs.begin("wifi", false);
  startWifi();
  if (MDNS.begin(HOSTNAME)) MDNS.addService("http", "tcp", 80);
  startServer();
  Serial.println("ready. In the web app enter this address and press Connect Wi-Fi. Type status for counters.");
}

void loop() {
  pumpMega();
  pollUsb();
  delay(1);
}
