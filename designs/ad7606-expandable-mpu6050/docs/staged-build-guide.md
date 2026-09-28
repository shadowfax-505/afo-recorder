> MPU variant: [mpu6050-wiring-and-timing.md](mpu6050-wiring-and-timing.md) is authoritative for sensor wiring, timing and current release gates. Inherited ADC/analog instructions remain applicable.

# AD7606: staged breadboard-to-PCB build

**Use [physical assembly](physical-assembly.md), [complete hole/wire tables](build-guide.html) and [module qualification](module-qualification.md).** Old stage SVGs are block overviews, not current insertion instructions. The viewer and revision-12 tables govern breadboard routing.

All instrument-connected tests use synthetic signals with no person attached. Remove all power before moving jumpers. Keep module links short (initial target≤50 mm), pair fast signals with ground, keep clock/decoupling on the ADC module, and do not construct switching loops on solderless breadboard. Never place an ammeter across a supply; insert it in series with the positive supply lead after powering down. Do not power modules through signal pins.

## Circuit correspondence

The final PCB specification is design/main.json. BB1–BB4 implement its four analog paths; BB0 implements midpoint buffering. DIP pin1 starts at e10, notch toward row9; a–e and f–j form separate5-hole strips per row. There are no implicit power-rail connections. Use breadboard/placements.csv and wiring.csv together. Every jumper lead has its own hole; strip-short and unique-hole checks are in breadboard/checks.json. External wiring is specified in system-wiring.csv; module pin names and connector orientation define the connection, not the rendered body position.

Populate four channels, enabling two initially. Each signal board has two unity followers and two RC stages; BAV199 requires a verified soldered carrier. Capacitor/filter tolerances match simulation. Components of different packages require their own footprint/pin review. Test-only substitutions and power/USB differences are documented in module-verification.md; the breadboard is electrical validation of these blocks, not a full replica of layout-dependent performance.

## Acceptance policy

Limits below are **provisional engineering screens**, not measured results or blanket manufacturer guarantees. Filter envelopes and ideal DC codes are calculated; rail limits follow the selected nominal rails and IC operating range. Noise/crosstalk/ripple/temperature thresholds are project targets requiring final review. Measure instrument bandwidth, calibration and uncertainty; record failures without widening limits to pass.

| Stage | Assembly and instrument connections | Gate before proceeding | Troubleshooting |
|---|---|---|---|
| [1. Power and midpoint](../breadboard/stages/stage-01.svg) | BB0 midpoint; regulated lab rails, no controller. Connect DMM across each rail/GND; scope ground spring at load. Initially 50 mA current limit, increase deliberately for dummy loads. | 3.3 V digital 3.23–3.43 V; 3.0 V analog 2.94–3.06 V; midpoint 1.47–1.53 V. Test 0/100/300 mA digital and 0/20/50 mA analog. Ripple targets ≤50/10 mVpp (20 MHz bandwidth); step deviation ≤5%, recovery ±3% within10 ms. Temperature <60°C after10 min at20–30°C ambient. 5 V ADC:4.8–5.2 V at10–50 mA; verify never above5.25 V including startup. | Check polarity, ground continuity, supply limits, load resistor rating and midpoint follower wiring. |
| [2. ESP32 controller](../breadboard/stages/stage-02.svg) | Add N8R8 controller; diagnostic-controller build. Attach USB with no person connected. Fit controls, LEDs, battery sense and USB detection circuit from schematic. Scope GPIO21 USB_PRESENT_N. | 20 program/reset cycles without failure. Buttons/LEDs respond. GPIO21 low when USB attached, high when absent. Recorder must refuse to start while USB attached; that interlock needs a repeat at stage7. Record measured current; no assumed universal current limit. | Check boot/reset levels, native USB pins and 3.3 V rail droop. |
| [3. ADC timing and DC](../breadboard/stages/stage-03.svg) | Complete module verification first. Add ADC and local reference/clock/decoupling. Connect known DC sources with common ground. Use diagnostic-adc-2ch then4ch. Scope trigger/DRDY, BUSY and SCLK. | Conversion triggers125 µs±1%;8 kHz±0.1% averaged60 s. BUSY completes before next trigger; read all128 bits; no timeout/overrun in60 s. At input 0.5 / 1.5 / 2.5 V, ideal codes 3277 / 9830 / 16384; allow ±65 codes plus source uncertainty (10 mV project screen). | Check serial mode, reset polarity, reference, logic levels and CS timing. AD7606 has no ID register/readback equivalent; test known DC codes and channel identity. |
| [4. First EMG channel](../breadboard/stages/stage-04.svg) | Add BB1 complete analog path. Signal generator RAW0:1.5 V DC +100 mVpp sine. DMM at RAW,BUF0A,BUF0B,AIN0P; scope both filter stages. Sweep20,100,500,1000,4000 Hz. Never attach electrodes. | DC gain1; two3.3k/47nF low-pass stages. Compare gain against simulations/results/response.csv tolerance envelope; allow additional±0.5 dB measurement/model margin. Unplugged RAW→1.50 V±30 mV after settling. Record RMS noise over20–500 Hz; provisional target<2 mVrms input-referred, to be reviewed for research suitability. Check clipping using safe0.1–2.9 V sources, never±5 V into3 V buffers. | Check DIP notch/pins, capacitor values, carrier orientation and offset. ADC mathematical clipping plots are not safe test-voltage instructions. |
| [5. Remaining EMG channels](../breadboard/stages/stage-05.svg) | Add BB2, then BB3/BB4. Fit all circuits; select2ch/4ch firmware. Inject100 Hz into only one input at a time, others biased at midpoint. | Enabled channels match physical ports; disabled channels absent from CSV/live display. Simultaneous channel samples share trigger/frame timestamp. Project crosstalk screen <−40 dB versus driven signal, with generator feedthrough measured separately. Zero unexplained errors in10 min each mode. | Check channel order, ground return, midpoint impedance and wire coupling; do not infer crosstalk from ideal simulation. |
| [6. Foot and shank IMUs](../breadboard/stages/stage-06.svg) | Add one ready-made IMU, then second. diagnostic-imu-one then diagnostic-imu-two. Logic analyzer on shared I²C and individual AD0/INT; rotate each known axis. | WHO_AM_I 0x68 at both addresses;200 Hz±2% over60 s, no FIFO overflow/errors. Stationary gravity-axis within±0.1g of±1g; cross axes within±0.1g, gyro per axis<5°/s before calibration. Verify axis signs and intended cable length. | Check I²C pull-ups, power, distinct addresses/interrupts, header map and cable integrity. |
| [7. SD recording](../breadboard/stages/stage-07.svg) | Add SD interface. Record synthetic inputs without USB; use2ch and4ch. Repeat with missing/full card and five controlled power interruptions on expendable media. | 60 min each mode, no unexplained SD sample loss, CRC errors or queue overflow. Refuse start without SD; report full-card stop. Recovery preserves complete valid records and reports truncated tail/missing END. Attach USB during synthetic recording: explicit stop. | Inspect card latency/rail droop, queues and reports. Never erase original fault evidence; filesystem recovery is not guaranteed. |
| [8. Wi-Fi and SD together](../breadboard/stages/stage-08.svg) | Join AFO-Recorder-B Wi-Fi on laptop; run python3 host/live_receiver.py. Maintain SD recording; congest/disconnect/reconnect wireless. | 60 min4ch: stage7 SD quality maintained; only enabled channels displayed; induced packet loss visible in counters/gaps. Compare SD versus laptop capture. | Check laptop firewall/UDP3333, network selection and queue counters. Wi-Fi copy is best effort. |
| [9. Battery runtime](../breadboard/stages/stage-09.svg) | Remove lab supply and all instrument/USB connections. Connect protected1S battery with verified polarity, external charging only. | Measured≥2 h intended-use runtime;20 startup/shutdown cycles; successful60 min trial; no unexpected reset. Record pack capacity, age, voltage, configuration and ambient temperature. | Check droop, protection trip and converter temperature. Battery time is not predicted by these simulations. |
| [10. MyoWare and wearable integration](../breadboard/stages/stage-10.svg) | Replace synthetic inputs with MyoWare RAW, first without person/electrodes. Verify polarity, sensor rail, cabling and clearance around AFO. | Secure strain relief/mounting; no cable pull on electrodes. Institutional approval, consent and electrical-safety review completed before supervised human testing. No charging or mains/USB/instrument cables attached to a person. | Resolve sensor saturation, movement artifacts and safety/mounting issues before wearable recordings. |

## Firmware and laptop use

ESP-IDF5.4.2. Prebuilt firmware/builds profiles have individual manifests and flash offsets. All provided prebuilt files identify hardware as `pcb`; rebuild with `-DAFO_HARDWARE=breadboard` for correct lab metadata. Do not alter interlocks for recording. Diagnostic profiles intentionally permit USB, never mount SD or start Wi-Fi, and do not require later modules.

```sh
idf.py -B build-controller -DAFO_DIAGNOSTIC_STAGE=2 -DAFO_HARDWARE=breadboard build
idf.py -B build-adc -DAFO_DIAGNOSTIC_STAGE=3 -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=breadboard build
idf.py -B build-four -DAFO_DIAGNOSTIC_STAGE=3 -DEMG_CHANNEL_COUNT=4 -DAFO_HARDWARE=breadboard build
idf.py -B build-imu -DAFO_DIAGNOSTIC_STAGE=6 -DAFO_IMU_COUNT=1 -DAFO_HARDWARE=breadboard build
idf.py -B build-record -DAFO_DIAGNOSTIC_STAGE=0 -DEMG_CHANNEL_COUNT=4 -DAFO_WIFI=1 -DAFO_HARDWARE=breadboard build
```

Stages4/5 use ADC diagnostics with new stimuli. IMU_COUNT=2 adds the second IMU. For stage7 compile AFO_WIFI=0. ADC diagnostics report means, range, RMS and fault counts; USB printing can affect timing, so recording/logic-analyzer tests are still mandatory.

```sh
python3 host/convert.py trial.afolog --help
python3 host/live_receiver.py --help
python3 host/live_receiver.py
```

Join the device network using the configured firmware credentials (see firmware/main/wifi_live.c). Receiver serves a local dashboard, stores received original records and tracks loss. Use the SD file as primary evidence. Host tools support legacy schema1, ADS schema2 and AD7606 schema3; only enabled channels are exported.

## Order gate

Fill docs/stage-results.csv and attach raw scope traces, logs and source recordings. Before recommending an order: confirm received hardware matches the selected parts and terminal maps; complete schematic/footprint/power-loop/USB/antenna/assembly reviews; rerun ERC/DRC/parity; sign off lab gates. After fabrication repeat power, analog noise/crosstalk, sustained recording, timing, wireless and thermal tests on the compact board. Neither DRC nor breadboard success establishes medical safety or patient fit.
