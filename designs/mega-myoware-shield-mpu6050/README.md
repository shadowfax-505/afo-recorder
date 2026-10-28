# Arduino Mega · MyoWare 2.0 shield · MPU-6050 · ZS-040 Bluetooth

A battery-powered bench setup that streams MyoWare 2.0 EMG and up to two MPU-6050 IMUs from an Arduino Mega 2560 to a browser over Bluetooth (or USB). The web app shows live readings and keeps recordings in the browser for later viewing and CSV export.

> **Status:** the sketch compiles for the Mega 2560 (arduino-cli 1.2.2, arduino:avr 1.8.8, no warnings) and its frame encoder is checked byte-for-byte against the web app's decoder. The web app passes a Playwright test against a synthetic stream and a simulated Web Serial port. **Nothing here has run on the physical board yet.** Sample rates, Bluetooth range, battery life and signal quality are unmeasured.

```text
firmware/mega_myoware_stream/   the sketch to flash (streams EMG + IMU)
firmware/hc05_setup/            optional: raise the ZS-040 to 115200 baud, rename it
web/                            the web app (static files, no build step)
host/tests/                     protocol and browser tests
```

## Parts (from the photos)

| Part | Notes |
|---|---|
| Arduino Mega 2560 | 5 V logic, 10-bit ADC (0–1023 over 0–5 V) |
| MyoWare 2.0 Arduino Shield | six 3.5 mm TRS jacks wired to A0–A5; each jack's tip carries the sensor's selected output |
| MyoWare 2.0 Muscle Sensor + Link Shield + TRS cable | the sensor's **OUTPUT** switch picks ENV, RECT or RAW for the cable |
| 2 × GY-521 (MPU-6050) | on the I²C bus |
| ZS-040 Bluetooth (HC-05 / HC-06) | serial over Bluetooth (SPP) |
| 3.7 V LiPo pouch cell (423450) | capacity print is overstamped in the photo |
| USB-C charger board (CA-033T) | charges the cell |
| XL6009 boost converter | raises the cell to 5 V for the Mega (owner-measured) |

## Wiring

What the photos show is marked **seen**; the rest is what the sketch assumes, so check it against the board.

| Signal | Mega pin | Source |
|---|---|---|
| MyoWare sensor (TRS) | shield jack **A0** by default; any of A0–A5 can be switched on in the app | seen: one sensor plugged into the shield |
| IMU SDA / SCL | **20 / 21** (same as the shield's SDA / SCL pins) | seen: orange SDA, green SCL, white VCC, blue GND on the GY-521 |
| IMU A address | AD0 to GND → **0x68** | confirmed by the owner (28 Oct 2026) |
| IMU B address | AD0 to **3.3 V** → **0x69** | owner has it on 5 V (28 Oct 2026); move it to the Mega's 3.3 V pin, see below |
| ZS-040 TXD → Mega RX, RXD → Mega TX | **Serial1 (19 RX, 18 TX)** | confirmed over the link (28 Oct 2026); the sketch also listens on Serial2 (17, 16) and Serial3 (15, 14) |
| ZS-040 VCC / GND | 5 V / GND | assumed |

Things to check before powering up:

1. **Two IMUs need different addresses, and AD0 must stay at 3.3 V.** IMU A's AD0 goes to GND (0x68) and IMU B's to the Mega's **3.3 V** pin (0x69). On the GY-521, AD0 connects straight to the MPU-6050, which runs at 3.3 V from the module's regulator. The MPU-6050 datasheet's absolute maximum for AD0 (and SDA/SCL) is VDD + 0.5 V, about 3.8 V, so 5 V on AD0 is out of spec. The app's IMU tile shows which addresses answered.
2. **ZS-040 RXD is 3.3 V logic.** Feed it from the Mega TX through a divider (for example 1 kΩ in series, 2 kΩ to GND). The ZS-040 TXD can go straight to the Mega RX.
3. **Not on pins 0 and 1.** Those are the USB port. If the module is there, move it to 18/19, otherwise flashing fails and the stream collides with USB.
4. **Boost output.** The XL6009 is set to 5 V, which suits the Mega's 5 V pin (that pin bypasses the regulator, so keep it at 5.0 V). It would be too low for VIN or the barrel jack, which need about 7–9 V.

## Flash the sketch

With arduino-cli on your computer, from the repository root:

```sh
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:mega designs/mega-myoware-shield-mpu6050/firmware/mega_myoware_stream
arduino-cli board list                     # find the port, e.g. COM5, /dev/ttyACM0 or /dev/cu.usbmodem101
arduino-cli upload -p COM5 --fqbn arduino:avr:mega designs/mega-myoware-shield-mpu6050/firmware/mega_myoware_stream
arduino-cli monitor -p COM5 -c baudrate=115200
```

On a Mac, pair the module in System Settings → Bluetooth (PIN 1234). It then appears as `/dev/cu.HC-05`, which Chrome lists in the Connect picker. On the first test it carried 29 samples per second at 9600 baud with no errors.

If `board list` shows nothing (it did on one Mac even with a genuine Mega attached), pass the port from `ls /dev/cu.usb*` straight to `-p`.

In the monitor you should see `# mega-myoware-1.0 ready. imu_mask=3.` (3 = both IMUs found, 1 = only A, 2 = only B, 0 = none). Type `p` and Enter to print CSV samples, `x` to stop.

## Bluetooth speed

The ZS-040 ships at 9600 baud, which fits about 20 samples per second with one EMG channel and both IMUs. That is enough for the MyoWare ENV output but not for RAW. Raising the module to 115200 gives about 245 samples per second:

1. Flash `firmware/hc05_setup`, open the monitor at 115200 with line ending "Both NL & CR".
2. HC-05 (the ZS-040 with a small button): hold the button while powering the module so its LED blinks slowly, then type `AT` (expect `[Serial1] OK`, which also tells you which port it is on), then `AT+NAME=AFO-MEGA` and `AT+UART=115200,0,0`.
3. Reflash `mega_myoware_stream` with `--build-property "compiler.cpp.extra_flags=-DBT_BAUD=115200UL"` (or change `BT_BAUD` at the top of the sketch).

Over USB the sketch always runs at 115200 and the same 245 samples per second limit applies. The sketch caps the rate to what the link can carry and the app shows the cap.

## Use the web app

The app needs Chrome or Edge on a computer (Web Serial). Serve it over HTTP or HTTPS, not from a `file://` path:

```sh
cd designs/mega-myoware-shield-mpu6050/web
python3 -m http.server 8770
# open http://localhost:8770/
```

Once this is merged to `main` it is also served by the project's GitHub Pages site at `/afo-recorder/designs/mega-myoware-shield-mpu6050/web/`.

1. **Pair the module** in your computer's Bluetooth settings (PIN `1234` or `0000`). Windows creates "Standard Serial over Bluetooth link" COM ports; the outgoing one is the one to use.
2. Press **Connect** and choose that COM port, the Bluetooth device, or the Mega's USB port. The app asks the board for its settings, then starts the stream.
3. Tick the EMG jacks in use and set the sample rate. **Try demo** streams synthetic signals if you want to look around without the board.
4. Type a name and notes, press **Record**, and press **Stop** when done. Samples are saved every 2 seconds, so a closed tab keeps everything up to the last save.
5. Open **Recordings** to view a recording (drag across a chart to zoom), export CSV, download a backup, rename or delete it.

Recordings live in that browser's storage on that computer. Use **Download backup** and **Import backup** to move them.

### CSV columns

`time_s` (board clock, from the first sample), `seq` (sample counter; a jump means samples were lost on the link), `flags` (bit 0 / bit 1 = IMU A / B read failed), then for each enabled jack `A<n>_counts` and `A<n>_volts` (counts × 5 / 1023), then for each IMU `ax ay az` in g (±4 g range) and `gx gy gz` in °/s (±500 °/s range).

## Serial protocol

Commands are single ASCII lines: `?` info, `s` binary stream, `p` CSV stream, `x` stop, `r<hz>` rate, `e<mask>` EMG jacks (bit n = An), `i` rescan IMUs. The board streams to whichever port sent the command. Binary frames are `A5 5A type len payload crc8`; the layout is documented in [`frame.h`](firmware/mega_myoware_stream/frame.h).

## Tests

```sh
node --test designs/mega-myoware-shield-mpu6050/host/tests/protocol.test.mjs   # needs g++
node designs/mega-myoware-shield-mpu6050/host/tests/webapp.e2e.mjs             # needs Playwright + Chromium
```

## Safety

Research prototype, not a medical device. Follow MyoWare's guidance: when electrodes are on a person, run the board from its battery and keep any laptop connected over USB unplugged from mains. Remove power before plugging or unplugging the TRS cables.
