# 06 - Foot IMU, then shank IMU

**Prerequisite:** Stage 5 accepted; ADC remains attached. **Firmware:** diagnostic-imu-one, then diagnostic-imu-two. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

6A: foot MIKROE-4237 carrier at 3.3 V, SPI jumpers verified. 6B: add shank. Test each in six static orientations and rotate one at a time. Capture separate INT1 lines. These diagnostics also run the ADC; they are not standalone IMU-only images.

## Acceptance checks

- **6-foot:** SPI JP2–JP4 1–2; 3.3 V; WHO_AM_I 0x47/readback; foot CS GPIO7 / INT1 GPIO16; correct axis signs
- **6-shank:** Shank CS GPIO15 / INT1 GPIO17; 200 Hz ±1% per sensor over 60 s; no FIFO/missing-IRQ/invalid-packet errors
- **6-stationary:** ±16 g / ±2000 °/s configured; gravity axis ±1 g within ±0.1 g, cross axes within ±0.1 g; gyro per axis <5 °/s before calibration

## Send for review

- WHO/readback serial results
- FIFO and interrupt counts over 60 s
- six-face accelerometer means
- stationary gyro means
- axis photographs
- raw IRQ/SPI timing capture

No shared sensor clock is assumed. Counter wraps and different startup counts are normal; equal row numbers do not identify simultaneous foot/shank samples.

## Continuous regression

Before power: inspect the changed wiring against the contact table and photograph it. After power: remeasure every connected rail at the load, verify no unexpected heat/current, and rerun the last accepted diagnostic. Repeat earlier affected tests whenever a supply, cable, firmware or grounding connection changes. Record failures and repairs; retain the previous accepted evidence.

## If the gate fails

Stop acquisition and remove power before changing wiring. Disconnect only the last-added module and restore the last accepted configuration. Repeat its test. If it now fails, check the shared supply/ground and changed connections before replacing components. Never change multiple modules at once to chase a fault.

## Results

Fill measurements.csv; retain raw instrument files alongside screenshots. Outcome starts NOT TESTED. Include units, uncertainty, instrument model/settings, source voltage/load, firmware hash and filenames. Mark unmet criteria FAIL; missing evidence PENDING. Submit the whole stage folder, including failures. A completeness check is not engineering approval.

## Stage files

- [New wires](new-wires.csv): exact endpoints copied from the existing wiring table; keep earlier accepted wires. Power-isolation and qualification instructions above override connection order within a stage.
- [Probe contacts](probe-contacts.csv): available exact probe locations. An empty table means use the instrument instructions above.
- [Fixture parts](fixture-parts.csv): staged discrete fixture components from the existing BOM; this is not a complete procurement list for modules, tools or consumables.
- [Measurements](measurements.csv) and [submission metadata](submission.json).
