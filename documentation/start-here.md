# Start here

The AFO Research Recorder captures MyoWare 2.0 RAW signals and foot/shank motion, saves the primary data to microSD, and sends a best-effort Wi-Fi copy to a laptop. It is an acquisition research prototype. It is not an AFO controller, medical device, or clinically validated system.

## 1. Choose one package

Make three decisions and stay within the resulting package.

### How many EMG channels?

- Choose a **fixed two-channel** AD7606 package if the study will use exactly two MyoWare sensors.
- Choose an **expandable** package if four physical analog inputs and a firmware-selectable two/four-channel mode are required.

### Which ADC?

- **AD7606:** 16-bit simultaneous sampling and a locally identified module for the lab prototype. Its exact received-board mode straps, VIO behavior, and serial header mapping still require qualification.
- **ADS131M04:** 24-bit simultaneous sampling with ADC-specific CRC/status handling. The lab carrier and its input-loading equivalence remain procurement and qualification dependencies.

### Which IMU?

- **ICM-42688-P:** SPI design with sensor timestamp-bearing packets. The exact carrier remains a procurement choice.
- **GY-521 / MPU-6050:** I²C design using the locally linked module. Timing is reconstructed from ESP32 interrupts and FIFO order; it does not contain a native sensor timestamp.

Both IMU families target 200 Hz for foot and shank. All packages target 8 kHz for each enabled EMG channel.

## 2. Understand the evidence labels

| Label | Meaning |
|---|---|
| Verified in software | A saved automated check, build, or test passed |
| Simulated | Generated data exercised a model or data path |
| Pending hardware | The value or behavior must be measured on the assembled system |
| Passed — measured | A person performed the lab procedure and saved the evidence |

Current evidence includes clean automated PCB-rule reports, host-tool tests, firmware builds, file-format checks, viewer checks, and named-wire consistency checks. It does not include a powered recorder, measured ADC noise, timing drift, SD endurance, Wi-Fi coexistence, or battery runtime.

## 3. Follow the staged build

Open the chosen package's `viewer/build.html`. Begin at Stage 1, even if the complete 3D assembly is visible. Each stage tells you what to add, which connections are new, what to measure, and what must pass before proceeding.

Do not build the complete breadboard and debug it as one unknown system. The stage order intentionally preserves earlier diagnostic firmware so a later fault can be isolated.

## 4. Use the correct files

- `breadboard/` defines the lab assembly and module-to-module connections.
- `firmware/` contains profiles for that package's ADC and IMU family.
- `host/` contains the matching converter and live receiver.
- `hardware/` and `manufacturing/` describe the compact PCB.
- `docs/` contains package-specific thresholds and module differences.

The DevKit breadboard uses GPIO47 for microSD CMD. The compact PCB uses GPIO38. Do not flash a PCB build into the breadboard and infer that the wiring is wrong.

## 5. Keep people out of early electrical tests

All instrument-connected work uses synthetic signals with no person attached. Disconnect charging cables, USB, and mains-connected instruments before electrodes are applied. Human recordings begin only after the required institutional approval, informed consent, and electrical-safety review.

## Next reading

Read [system architecture](system-architecture.md), then [lab build guide](lab-build-guide.md), [firmware build guide](firmware-build-guide.md), [recording and analysis](recording-and-analysis.md), and [validation status](validation-status.md). Read [SD card wiring](sd-card-wiring.md) before Stage 7 and the chosen package's module qualification guide before connecting a module.

For a local website, run `python3 -m http.server 8769` from the repository root and open <http://127.0.0.1:8769/>. Do not use a `file://` URL for the 3D viewers.
