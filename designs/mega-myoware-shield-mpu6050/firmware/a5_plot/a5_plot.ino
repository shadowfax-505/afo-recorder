// a5_plot: read the shield's A5 jack and print it for the Arduino Serial
// Plotter. Nothing else runs: no IMUs, no Bluetooth, no binary frames.
//
// Open Tools > Serial Plotter (or `arduino-cli monitor -p <port> -c baudrate=115200`)
// at 115200 baud. Each line is "A5_volts:<v>", sampled 500 times a second.

const uint8_t PIN = A5;
const unsigned long PERIOD_US = 2000;  // 500 Hz

unsigned long next;

void setup() {
  Serial.begin(115200);
  next = micros();
}

void loop() {
  if ((long)(micros() - next) < 0) return;
  next += PERIOD_US;

  int counts = analogRead(PIN);         // 0..1023 over 0..5 V
  float volts = counts * 5.0 / 1023.0;
  Serial.print(F("A5_volts:"));
  Serial.println(volts, 3);
}
