# Changelog

## Recording shutdown and finalization — v0.1.4 — 30 September 2026

- Keep acquisition task handles valid until the owner joins and deletes suspended workers; latch faults to stop acquisition.
- Attempt both IMU stop calls even if the foot device reports an error.
- Sync queued data before END; publish the wireless stop verdict after final write/sync/close checks, including storage failures.
- Pass 38 native production-recorder cases across PCB and breadboard profiles; 300 lifecycle cycles pass actual ESP-IDF FreeRTOS in Wokwi. Rebuild the three recording profiles; four diagnostic binaries and prior sensor traces are unchanged.
- Add a recording/recovery report, synthetic fixtures, stop-code guide and reproducible tests. Physical validation remains pending; the five other designs are unchanged.

## Two-channel AD7606 / ICM refinement — 30 September 2026

- Corrected analog metadata, ADC fault handling, diagnostic acquisition windows and the initial IMU interrupt grace period.
- Rebuilt the selected variant's seven firmware profiles and regenerated manufacturing exports.
- Added a direct schematic/PCB/GPIO audit, expanded ngspice checks, a RAW-voltage regression test, Wokwi behavioral models and a shorter lab guide.
- Wokwi firmware execution remains unresolved after SPI2 MISO contention; native model checks and firmware compilation are not a passing virtual recorder test. Physical measurements remain pending.
- Other five design packages remain unchanged.

## Documentation update — 29 September 2026

- Rewrote the repository README around scope, configuration choice, build order, validation language, safety, and repository navigation.
- Added a project-manual index and contribution guidance.
- Added a responsive live manual covering configuration selection, architecture, staged construction, firmware, data conversion, validation, and safety.
- Added documentation links to every guided build, assembly viewer, and PCB preview.
- Kept automated, simulated, and physically measured evidence explicitly separate.

## Interaction update — 28 September 2026

- Required a double-click to open a single board from the whole assembly while retaining single-click inspection for wires and modules.
- Verified this behavior across all six viewers.

## Public engineering preview — 28 September 2026

- Published all six configurations and the static project site.
- Attached complete ZIP packages to the `v0.1.0` prerelease.
- Preserved third-party notices, source references, and validation limits.

### Simulation evidence safeguards — 30 September 2026

The selected two-channel AD7606/ICM runner now uses fresh output directories and rejects stale or partial results, incorrect sample/channel checks and empty traces. Fourteen synthetic evidence-gate regression tests pass. These are not additional hardware or ESP32 simulation passes; the Wokwi SPI contention remains unresolved. Firmware and PCB files are unchanged from v0.1.1.

Nine native test groups execute the unchanged production ADC driver with mocked timer/BUSY/SPI events; all pass. Real-time concurrency and electrical behavior remain outside this test.

### Actual ESP32-S3 simulation — 30 September 2026

Seven AD7606 two-channel/ICM diagnostic scenarios pass Wokwi CLI, with serial and VCD protocol evidence. Initialize mode-2 SPI during reset to prevent a shifted first sample; latch diagnostic worker errors across tasks. Rebuild all seven firmware profiles; 40 host tests, 15 runner tests, ten driver test groups and fresh circuit checks pass. Analyzer coverage and remaining physical/SDMMC/Wi-Fi limits are explicit in the new execution report.

### Current integrated web verification — 1 October 2026

All 18 current v1.6 AD7606/two-channel/ICM integrated cases pass with complete exports and actual converter/live-decoder checks. Separate session buffers from startup stack allocation; rebuild all seven profiles and rerun native control checks. Add reproducible web files, current socket/API/browser/archive tests that retain explicit wireless loss, and an honestly unqualified QEMU experiment. Preserve earlier source/image identities, incomplete CLI outcomes and the other five designs. No physical measurements or board orders.
