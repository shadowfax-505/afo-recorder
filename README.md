# AFO Research Recorder

An engineering research platform for synchronized lower-limb EMG and motion acquisition. The recorder samples two MyoWare 2.0 RAW channels by default, supports foot and shank IMUs, stores the primary recording on microSD, and sends a best-effort live copy over ESP32-S3 Wi-Fi.

[Open the live project](https://shadowfax-505.github.io/afo-recorder/) · [Read the documentation](https://shadowfax-505.github.io/afo-recorder/documentation/) · [Download complete packages](https://github.com/shadowfax-505/afo-recorder/releases/tag/v0.1.6)

> **Engineering status:** the firmware, file format, host tools, PCB rules, wiring data, simulations, and browser viewers have automated evidence. No recorder has yet passed the physical bench sequence. This repository does not claim measured signal quality, runtime, wearable safety, or clinical performance.

## What is included

| Layer | Included | Current evidence |
|---|---|---|
| Acquisition | ESP32-S3 firmware for AD7606 or ADS131M04 and two IMU families | Released profiles compile; hardware timing remains unmeasured |
| Storage | Versioned binary records, counters, metadata, CRC, and interrupted-file recovery | Converter and fault-injection tests pass |
| Live view | Best-effort Wi-Fi receiver for a laptop | Loopback/software checks only |
| Hardware | Breadboard plans, compact PCB projects, manufacturing exports, and 3D viewers | ERC/DRC and consistency checks pass; fabrication review remains open |
| Lab workflow | Ten gated stages from power rails to MyoWare integration | Procedures and result sheets supplied; measured results are blank |

## Choose a configuration

All packages target 8 kHz per enabled EMG channel and 200 Hz from each foot/shank IMU.

| ADC | EMG capacity | Motion sensor | Package |
|---|---:|---|---|
| AD7606, 16-bit simultaneous | Fixed 2 | ICM-42688-P | `ad7606-two-channel-icm42688` |
| AD7606, 16-bit simultaneous | Fixed 2 | GY-521 / MPU-6050 | `ad7606-two-channel-mpu6050` |
| AD7606, 16-bit simultaneous | 2 or 4 | ICM-42688-P | `ad7606-expandable-icm42688` |
| AD7606, 16-bit simultaneous | 2 or 4 | GY-521 / MPU-6050 | `ad7606-expandable-mpu6050` |
| ADS131M04, 24-bit simultaneous | 2 or 4 | ICM-42688-P | `ads131m04-expandable-icm42688` |
| ADS131M04, 24-bit simultaneous | 2 or 4 | GY-521 / MPU-6050 | `ads131m04-expandable-mpu6050` |

Use one package end to end. Do not combine an ICM wiring plan with MPU firmware or a breadboard binary with the compact-PCB SD pin assignment. The fixed-two packages intentionally reject four-channel builds.

### Arduino Mega bench setup

A separate, simpler setup lives in [`designs/mega-myoware-shield-mpu6050`](designs/mega-myoware-shield-mpu6050/README.md): an Arduino Mega 2560 with the MyoWare 2.0 Arduino Shield, up to two MPU-6050 IMUs and a ZS-040 Bluetooth module, plus a browser app for live readings and saved recordings. It uses the Mega's 10-bit ADC at up to a few hundred samples per second, so it is not a substitute for the six packages above.

## Start here

1. Read the [project manual](documentation/README.md) and choose one package.
2. Open that package's `viewer/build.html` and begin at Stage 1.
3. Qualify each module before attaching it to the controller.
4. Use synthetic signals with no person attached for every instrument-connected test.
5. Record actual measurements and pass every stage before ordering the compact PCB.

For a local copy of the website:

```sh
python3 -m http.server 8769
```

Then open <http://127.0.0.1:8769/>. The 3D viewers require HTTP and do not work correctly from a `file://` URL.

## Repository map

```text
designs/<configuration>/
├── breadboard/      terminal-level plans, placements, and wire tables
├── firmware/        ESP-IDF source and build profiles
├── hardware/        KiCad source and module references
├── host/            converter, live receiver, plots, and tests
├── manufacturing/   Gerber, drill, BOM, placement, and STEP exports
├── simulations/     analog and acquisition fault models
├── docs/            package-specific build and validation records
└── viewer/          guided build, 3D assembly, and PCB preview

documentation/       project-wide manual, status, and evidence summaries
validation/          blank or user-entered bench-session records
design-catalog.json  machine-readable list of all six configurations
```

## Validation language

The focused **AD7606 / fixed two-channel / ICM-42688-P** build has a [current integrated verification report](designs/ad7606-two-channel-icm42688/docs/integrated-verification.md). Its laboratory firmware is now **ad7606-2ch-1.12**, and **all 18 integrated Wokwi cases pass on its simulation image** (12 October 2026; the 1.11 run exposed a Wi-Fi preview race that 1.12 fixes) (32/30 µs ICM-42688 timestamp ticks, 2.44 s PSRAM record queue, per-device Wi-Fi password, IMU-only bench verdicts at the datasheet’s ±2 % clock tolerance, fitted IMU host time); its [ICM-42688-P setup](designs/ad7606-two-channel-icm42688/docs/icm-module.md) was checked against the official TDK datasheet (DS-000347 rev 1.6) and a register-level sensor model, and its AD7606 against ADI’s Rev. G data sheet. Following ADI AN-1091, the PCB now holds the ADC in shutdown until the firmware releases STBY on GPIO14, and a BAT760 diode limits VDRIVE − AVCC during power-up (DRC/ERC clean; not yet built). It compiles and passes the host and native tests but has not been rerun in Wokwi. All 18 v1.6 cases pass actual ESP-IDF execution in Wokwi’s web simulator, with real FreeRTOS/FatFS/lwIP and documented sensor, storage and radio substitutes. Nominal saved acquisition has no detected sample loss; current laptop socket/API/browser/archive checks correctly retain preview and packet gaps. Local coverage includes a 60-second, 480,000-frame production-driver pipeline. The unqualified QEMU timing experiment and historical incomplete CLI runs remain visible. Physical performance remains unmeasured; On 12 October 2026 the three other AD7606 designs received the same STBY/supply-ramp PCB fix and firmware (dual-1.4 / mpu6050-1.4); the ADS131M04 designs need none. On 11 October 2026 the other five designs received the shared firmware fixes (PSRAM record queue, per-device Wi-Fi password, metadata limit; 32/30 µs ticks for the ICM designs) and the fixed-two recorder corrections (worker lifecycle, fault latching, AD7606 BUSY confirmation, windowed diagnostics) and were rebuilt (firmware dual-1.3 / mpu6050-1.3); their other evidence is unchanged.

- **Verified in software** means a check, build, simulation, or test has a saved result in this repository.
- **Simulated** means generated inputs exercised a model or data path; it is not a hardware measurement.
- **Pending hardware** means the result must be measured on the assembled module, breadboard, or PCB.
- **Passed — measured** should be entered only by the person who performed the lab procedure and retained the evidence.

The latest project-level evidence reports six host suites with 242 tests, 26 compiled recording profiles, clean ERC/DRC reports for all six variants, and complete named wiring inventories. The same evidence explicitly marks physical validation as pending.

## Safety and research use

Disconnect charging cables, USB, and mains-connected instruments while electrodes are attached. Early electrical tests use synthetic sources with no person attached. Human recordings require appropriate institutional approval, informed consent, and an electrical-safety review. This system is a research recorder, not a medical device or an AFO controller.

## Documentation and attribution

- [Project manual and reading order](documentation/README.md)
- [System architecture](documentation/system-architecture.md)
- [Staged lab build](documentation/lab-build-guide.md)
- [Recording and analysis](documentation/recording-and-analysis.md)
- [Validation status](documentation/validation-status.md)
- [Manufacturer evidence](documentation/manufacturer-evidence.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

Project lead: **Muttakin Rahman**. Manufacturer credits, source references, and third-party licence notices are retained. Publication does not change the ownership of external boards, CAD, datasheets, libraries, or photographs.

Open the [complete-system guide](designs/ad7606-two-channel-icm42688/docs/whole-system.md) for the physical assembly, saved Wokwi scene and downloadable simulation bundle.

The latest focused checks include a [complete-scene digital timing capture](designs/ad7606-two-channel-icm42688/docs/digital-timing.md) and a [saved-data interpretation guide](designs/ad7606-two-channel-icm42688/docs/data-interpretation.md). The independent audit checks 21,116 original record CRCs and CSV rows across two synthetic captures. Downloadable examples include binary recordings, metadata, quality reports and readable analysis tables; original measurement bytes are preserved. Physical storage, signal accuracy and timing calibration remain pending.


## Active build: sequential development

The [AD7606 two-channel / ICM-42688-P workbook](designs/ad7606-two-channel-icm42688/development/README.md) organizes assembly, exact new wires, measurements and evidence review one module at a time. Read the [personal system explanation](designs/ad7606-two-channel-icm42688/docs/understanding-the-recorder.md) for the AFO and neuromuscular research rationale. The other five configurations remain unchanged.
