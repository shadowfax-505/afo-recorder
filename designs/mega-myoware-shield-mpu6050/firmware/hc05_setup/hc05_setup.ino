// ZS-040 (HC-05 / HC-06) setup bridge for the Arduino Mega.
//
// Opens Serial1, Serial2 and Serial3 at the same baud and bridges them to the
// USB Serial Monitor (115200, "Both NL & CR"). Whatever you type goes to all
// three ports; replies are printed with the port they came from, so this also
// tells you which port the module is wired to.
//
// HC-05 (ZS-040 with a button): hold the button while powering the module so
// its LED blinks slowly (about every 2 s). That is AT mode at 38400 baud:
//   AT                     -> OK
//   AT+NAME=AFO-MEGA       -> OK
//   AT+UART=115200,0,0     -> OK   then set BT_BAUD 115200 in the main sketch
// HC-06 (no button): stays at its data baud (9600 by default). Type ~9600 to
// switch the bridge, then AT+BAUD8 (115200) with "No line ending".
//
// Type ~<baud> (for example ~9600) to change the bridge baud.

const unsigned long USB_BAUD = 115200;
unsigned long linkBaud = 38400;
HardwareSerial* links[] = {&Serial1, &Serial2, &Serial3};
const char* names[] = {"Serial1", "Serial2", "Serial3"};
char line[32];
uint8_t len = 0;

void openLinks() {
  for (uint8_t i = 0; i < 3; i++) {
    links[i]->end();
    links[i]->begin(linkBaud);
  }
  Serial.print(F("# bridge at "));
  Serial.print(linkBaud);
  Serial.println(F(" baud on Serial1, Serial2 and Serial3"));
}

void setup() {
  Serial.begin(USB_BAUD);
  openLinks();
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (len == 0 && c == '~') {
      line[len++] = c;
      continue;
    }
    if (len > 0) {
      if (c == '\n' || c == '\r') {
        line[len] = 0;
        long b = atol(line + 1);
        if (b > 0) {
          linkBaud = (unsigned long)b;
          openLinks();
        }
        len = 0;
      } else if (len < sizeof(line) - 1) {
        line[len++] = c;
      }
      continue;
    }
    for (uint8_t i = 0; i < 3; i++) links[i]->write(c);
  }
  for (uint8_t i = 0; i < 3; i++) {
    if (!links[i]->available()) continue;
    Serial.print('[');
    Serial.print(names[i]);
    Serial.print(F("] "));
    while (links[i]->available()) {
      Serial.write(links[i]->read());
      delay(2);
    }
  }
}
