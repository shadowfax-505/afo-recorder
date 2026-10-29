// a5_bt_terminal: send jack A5 as plain text over the ZS-040 (HC-05) so a
// Bluetooth terminal app can show it. Nothing else runs: no IMUs, no
// binary frames, no web app.
//
// ZS-040 TXD -> Mega 19 (RX1), RXD -> Mega 18 (TX1) through a divider,
// as in the design README. Each line looks like "A5: 512  2.502 V" and is
// sent 20 times a second, to Bluetooth and to USB (115200) at the same time.

const uint8_t PIN = A5;
const unsigned long BT_BAUD = 9600;   // ZS-040 factory setting
const unsigned long PERIOD_MS = 50;   // 20 lines a second; 9600 baud fits about 50

unsigned long next;

void setup() {
  Serial.begin(115200);
  Serial1.begin(BT_BAUD);
  Serial1.println(F("A5 over Bluetooth ready"));
  Serial.println(F("A5 over Bluetooth ready"));
  next = millis();
}

void loop() {
  if ((long)(millis() - next) < 0) return;
  next += PERIOD_MS;

  int counts = analogRead(PIN);         // 0..1023 over 0..5 V
  float volts = counts * 5.0 / 1023.0;

  char line[32];
  char v[8];
  dtostrf(volts, 5, 3, v);              // AVR printf has no %f
  snprintf(line, sizeof line, "A5: %4d  %s V", counts, v);
  Serial1.println(line);
  Serial.println(line);
}
