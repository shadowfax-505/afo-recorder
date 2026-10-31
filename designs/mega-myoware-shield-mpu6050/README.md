# Arduino Mega · MyoWare 2.0 shield · MPU-6050 · ZS-040 Bluetooth

A battery-powered bench setup that streams MyoWare 2.0 EMG and up to two MPU-6050 IMUs from an Arduino Mega 2560 to a browser over Bluetooth (or USB). The web app shows live readings and gait parameters (heel strike, toe-off, stride, stance and swing time, cadence, double support, stride length, gait speed), and keeps recordings in the browser for later viewing, gait analysis and CSV export.

> **Status:** the sketch compiles for the Mega 2560 (arduino-cli 1.2.2, arduino:avr 1.8.8, no warnings) and its frame encoder is checked byte-for-byte against the web app's decoder. The web app passes a Playwright test against a synthetic stream and a simulated Web Serial port. **Nothing here has run on the physical board yet.** Sample rates, Bluetooth range, battery life and signal quality are unmeasured.

```text
firmware/mega_myoware_stream/   the sketch to flash (streams EMG + IMU)
firmware/hc05_setup/            optional: raise the ZS-040 to 115200 baud, rename it
firmware/esp32_wifi_bridge/     optional: ESP32 DevKitC that carries the stream over Wi-Fi
firmware/a5_plot/               optional: plot only jack A5 in the Arduino Serial Plotter
firmware/a5_bt_terminal/        optional: send only jack A5 as text to a Bluetooth terminal app
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
| ZS-040 TXD → Mega RX, RXD → Mega TX | **Serial1 (19 RX, 18 TX)** | confirmed over the link (28 Oct 2026); Serial3 (15, 14) also works. Serial2 is kept for the ESP32 (below) |
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

In the monitor you should see `# mega-myoware-1.2 ready. imu_mask=3.` (3 = both IMUs found, 1 = only A, 2 = only B, 0 = none). Type `p` and Enter to print CSV samples, `x` to stop.

## Wi-Fi through an ESP32 (optional)

An ESP32 DevKitC on the Mega's Serial2 carries the same stream over Wi-Fi, at the full rate (Serial2 runs at 500000 baud, exact on a 16 MHz Mega). The Bluetooth module stays on Serial1, and the app can use either link.

| Mega | ESP32 DevKitC | Note |
|---|---|---|
| 16 (TX2) | GPIO16 (RX2) | **through a divider**: 1 kΩ in series, 2 kΩ from GPIO16 to GND (5 V → 3.3 V) |
| 17 (RX2) | GPIO17 (TX2) | direct; the Mega reads 3.3 V as high |
| GND | GND | shared ground |
| 5 V (XL6009) | 5V | Wi-Fi peaks are about 250 mA; don't also plug in the ESP32's USB |

On a DevKitC with an ESP32-**WROVER** module, GPIO16/17 belong to its PSRAM: use GPIO25 (RX) and GPIO26 (TX) and set `MEGA_RX_PIN` / `MEGA_TX_PIN` in the sketch.

Flash the bridge (board "ESP32 Dev Module", esp32 core 3.x, no extra libraries; it compiles with 3.3.12):

```sh
arduino-cli core install esp32:esp32 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli compile --fqbn esp32:esp32:esp32 designs/mega-myoware-shield-mpu6050/firmware/esp32_wifi_bridge
arduino-cli upload -p /dev/cu.usbserial-XXXX --fqbn esp32:esp32:esp32 designs/mega-myoware-shield-mpu6050/firmware/esp32_wifi_bridge
```

Also flash the Mega with mega_myoware_stream 1.2 or later (that sets Serial2's speed).

**Its own network (default).** The ESP32 makes a network called `AFO-MEGA` (password `afo-mega-1`). Join it from the computer, open the app from http://localhost, type `192.168.4.1` in the ESP32 box and press **Connect Wi-Fi**.

**Your own Wi-Fi.** Open the ESP32's USB port at 115200 (`arduino-cli monitor -p … -c baudrate=115200`) and type `ssid YourNetwork`, `pass YourPassword`, `restart`. It prints its IP address; `afo-mega.local` also works on a Mac. `forget` goes back to its own network and `status` shows byte counters. http://afo-mega.local/ shows the same status in a browser.

Limits: browsers do not allow a `ws://` link from an `https://` page, so use the app from http://localhost (as now), not the GitHub Pages copy, for Wi-Fi. One app at a time can connect; a new connection replaces the old one. The bridge has been compiled and the app tested against a simulated bridge; it has not yet run on the real ESP32.

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

`time_s` (board clock, from the first sample), `seq` (sample counter; a jump means samples were lost on the link), `flags` (bit 0 / bit 1 = IMU A / B read failed), then for each enabled jack `A<n>_counts` and `A<n>_volts` (counts × 5 / 1023), then for each IMU `ax ay az` in g (±8 g range from firmware 1.1, ±4 g in 1.0) and `gx gy gz` in °/s (±500 °/s range).

## Gait analysis

The **Gait analysis** panel (Live tab and each recording) implements the pipeline in the reference papers the owner supplied (`gait-papers.pdf`, 30 Oct 2026):

- Quiguanas-López et al., *Feasibility of gait analysis for children with cerebral palsy using inertial measurement units*, Results in Engineering 29 (2026) 109173: two MPU-6050s above the lateral malleoli at 100 Hz, Python gaitmap pipeline, spatio-temporal parameters by its Eqs. 1–4.
- Carcreff et al., *What is the best configuration of wearable sensors to measure spatiotemporal gait parameters in children with cerebral palsy?*, Sensors 18 (2018) 394: the "Shanks" event detection (Salarian et al.) and the "Feet" de-drifted double integration (Mariani et al.).
- Küderle et al., *Gaitmap — an open ecosystem for IMU-based human gait analysis and algorithm benchmarking*, IEEE OJEMB 5 (2024) 163.

**Sensor placement.** One IMU on each shank, just above the outer ankle bone, as in Fig. 1 of the first paper. Pick which IMU is on which leg in the panel (the owner's physical labels are the reverse of the app's, see Wiring). Start each trial by standing still for about 2 s.

**What the code does** ([`web/gait.js`](web/gait.js)):

| Step | Paper | Here |
|---|---|---|
| Bias correction | gyro offset from a resting window at the start | per-axis mean of the stillest 1 s window |
| Axis alignment | gaitmap orientation alignment, PCA, forward-direction correction | PCA of the gyro gives the medio-lateral axis; sign set so mid-swing peaks are positive |
| Gait sequences | `UllrichGaitSequenceDetection` (dominant frequency, peak prominence, window) | 4 s windows with a clear dominant stride frequency (0.35–2.5 Hz) and enough motion |
| Events | peak detection on shank pitch angular velocity (Carcreff, Shanks) | mid-swing = large positive peak; HS = minimum after it; TO = minimum before it; sub-sample refined |
| Stride segmentation | pre-trained HMM (gaitmap) | choose in the panel: **Peak rules** (from consecutive mid-swing peaks, the default) or **Trained HMM**, an exact port of gaitmap's published model (below) |
| Stride / stance / swing | Eqs. 1–3 | per stride, with plausibility limits (0.45–3 s, stance 30–85 %) |
| Mean stride length | Eq. 4: distance ÷ strides | enter the walk distance (e.g. 10 m) in the panel |
| Gait speed | distance over time | walk distance ÷ time from first to last heel strike |
| Cadence | strides per minute | shown as strides/min and steps/min |
| Stride length per stride | Feet configuration: de-drifted double integration between zero-velocity instants | same, in the sagittal plane between mid-stance instants of the ankle-level sensor (an estimate; see below) |

With both legs it also gives step time, double support and stance/swing symmetry. **Export gait CSV** on a recording writes one row per stride.

**What this setup cannot do, or only approximately:**

- **Sample rate.** The papers used 100 Hz. Over the ZS-040 at 9600 baud the stream is about 20–29 Hz, which adds roughly ±20 ms to each event and about ±3 % to stance/swing percentages in the tests. Raise the module to 115200 (see Bluetooth speed) for about 245 Hz.
- **Sensor stride length is an estimate.** The Feet method assumes the sensor is still at mid-stance, which holds for a foot sensor. Just above the ankle it is nearly but not exactly still, so expect a bias of several centimetres per stride. It has not been checked against a walkway or motion capture. Eq. 4 with a measured distance is the reference method from the paper.
- **Thigh-based methods** (the ShTh double pendulum model, knee and thigh angles, knee range of motion) need sensors on the thighs. With only two IMUs you can have both shanks or one shank and thigh, not both.
- **Foot features** from the Feet configuration (foot clearance, foot angles at strike and off, turning angle) need IMUs on the feet; turning angle also needs a magnetometer, which the MPU-6050 does not have.
- **`HerzerEventDetection`** is written for foot-mounted sensors; it is replaced here by the shank-specific event rules above.
- **Validation equipment** in the papers (25 fps optical capture, Vicon, force plates, GaitRite) and the clinical scales (GMFCS, GMFM, MACS, FMS, WeeFIM) are outside this setup. Scale scores can be typed into a recording's notes.
- **Accelerometer range.** Firmware 1.0 set ±4 g, which an ankle sensor can exceed in swing. Firmware 1.1 sets ±8 g; strides with clipped samples are reported and get no sensor length.

**Trained stride model (gaitmap HMM).** [`web/hmm.js`](web/hmm.js) is a JavaScript port of gaitmap's `HmmStrideSegmentation` with `PreTrainedRothSegmentationModel` (Roth et al., J NeuroEng Rehabil 18, 93, 2021), and [`web/models/roth-hmm.js`](web/models/roth-hmm.js) holds that model's published numbers, copied unchanged from gaitmap_mad 2.6.0's `fallriskpd_at_lab_model.json` by [`host/tools/export_gaitmap_hmm.py`](host/tools/export_gaitmap_hmm.py). It filters the sagittal gyro (4th-order Butterworth, 10 Hz), resamples to 51.2 Hz, takes the signal and its 0.2 s slope, z-scores both, and decodes 5 "between strides" and 20 "in a stride" states, each a 2-D Gaussian mixture, with Viterbi. A stride runs from one pre-swing gyro minimum (about toe-off) to the next. Inside each one the app then finds mid-swing, heel strike and toe-off with the same rules as the peak method, so only *which* strides are counted changes, not how they are timed. On gaitmap's own example recording and on simulated shank walks at 60, 100 and 245 Hz the port gives the same states and the same strides as gaitmap itself (`host/tests/hmm.test.mjs`; the reference output in `host/tests/fixtures/` came from gaitmap 2.6.0 under Python 3.9 with pomegranate 0.14.6). Limits:
- It needs at least 51.2 samples per second; below that the app says so and uses the peak rules. Over the ZS-040 that means 115200 baud.
- It was trained on foot sensors of people with Parkinson's disease walking in a lab. This setup has shank sensors and is for children with cerebral palsy, so it is offered to compare against the peak rules, not as validated here. Retraining on your own labelled walks is the next step if it is to be trusted.
- It only counts whole toe-off-to-toe-off strides, so when a recording stops mid-stride it can miss the last stride of each leg that the peak rules still get.
- Because each recording is z-scored, it can label swaying or fidgeting as strides; those are dropped by the app's mid-swing (> 50 °/s), stride time and stance-% checks.
- gaitmap_mad is AGPL-3.0-or-later, so `hmm.js` and the model file are too (see `THIRD_PARTY_NOTICES.md`). If you host the app for other people, offer them the source; this public repository does.

The tests in `host/tests/gait.test.mjs` check the pipeline against synthetic shank signals with known events and stride length (`web/gaitsim.js`, which also drives the demo) at 29, 100 and 245 Hz. That shows the code does what it says; it does not show agreement with a real walk.

## Serial protocol

Commands are single ASCII lines: `?` info, `s` binary stream, `p` CSV stream, `x` stop, `r<hz>` rate, `e<mask>` EMG jacks (bit n = An), `i` rescan IMUs. The board streams to whichever port sent the command. Binary frames are `A5 5A type len payload crc8`; the layout is documented in [`frame.h`](firmware/mega_myoware_stream/frame.h).

## Tests

```sh
node --test designs/mega-myoware-shield-mpu6050/host/tests/protocol.test.mjs   # needs g++
node --test designs/mega-myoware-shield-mpu6050/host/tests/gait.test.mjs
node --test designs/mega-myoware-shield-mpu6050/host/tests/hmm.test.mjs
node --test designs/mega-myoware-shield-mpu6050/host/tests/wifi.test.mjs
node designs/mega-myoware-shield-mpu6050/host/tests/webapp.e2e.mjs             # needs Playwright + Chromium
```

## Safety

Research prototype, not a medical device. Follow MyoWare's guidance: when electrodes are on a person, run the board from its battery and keep any laptop connected over USB unplugged from mains. Remove power before plugging or unplugging the TRS cables.
