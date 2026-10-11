# Changelog

## Shared fixes for the other five designs — 11 October 2026

- Applied to `ad7606-expandable-icm42688`, `ad7606-expandable-mpu6050`, `ad7606-two-channel-mpu6050`, `ads131m04-expandable-icm42688` and `ads131m04-expandable-mpu6050`: PSRAM record queue of 20,480 records (about 2.44 s), no compiled Wi-Fi password (per-device password generated on first boot, stored in NVS, printed on the USB console), and a live-metadata limit with a host test that compiles the real metadata for every profile.
- MPU-6050 packages: their session metadata (about 1,360–1,430 bytes) exceeded the previous 1,280-byte limit, so the published firmware disabled the Wi-Fi preview on every recording. The limit is now 1,800 bytes (the metadata datagram is IP-fragmented).
- ICM-42688 packages: FIFO timestamp ticks are converted as 32/30 µs; their converter now honours `imu_timestamp_tick_us` and reports an `imu_clock` screen.
- Firmware identities `dual-1.2` and `mpu6050-1.2`; all 47 profiles rebuilt and cross-compiled only. These packages keep the earlier recorder generation and lack the later fixed-two lifecycle and BUSY-confirmation corrections.

## IMU timestamp scale, two-channel AD7606 / ICM firmware 1.8 — 11 October 2026

- Convert ICM-42688 FIFO timestamp ticks as 32/30 µs instead of 1 µs. TDK's ICM-426xx driver states the ICM-42688 PLL runs at 19.2 MHz rather than 20.48 MHz; treating ticks as 1 µs compressed IMU host-time estimates by 6.25% (about 62 ms per second after anchoring). Stage 6 measures the scale; one constant in `imu_timing.h` changes it.
- Record `imu_timestamp_tick_us` 1.0666667 in session metadata; the converter honours it, and older files default to 1 µs.
- Stage 6/7 acceptance now expects about 4,687.5 ticks per 200 Hz sample and a counter wrap every 69.9 ms. 47 host tests, nine IMU timing groups, 16 ADC groups (ASan/UBSan), 38 native recorder cases and both offline pipelines pass. Physical validation remains pending; the five other designs are unchanged.

## Verification fixes, two-channel AD7606 / ICM firmware 1.7 — 10 October 2026

- Moved the SD record queue to PSRAM and enlarged it from 2,048 to 20,480 records (about 0.244 s to 2.44 s); the old queue was shorter than the SD specification's 250-500 ms write-busy allowance.
- Removed the compiled-in Wi-Fi password. Each recorder generates a random 16-character password on first boot, stores it in NVS and prints it on the USB console.
- Raised the live-metadata limit from 1,280 to 1,400 bytes (one Wi-Fi MTU); metadata is built by `metadata.c` and a host test enforces a 64-byte margin.
- Added IMU timestamp-scale checks: diagnostic IMU lines report `tick_step_mean` and `host_us_per_tick`; the converter's quality report adds `imu_clock`.
- Stage acceptance now covers a full 2-hour SD run, final queue occupancy, card identity, the external GPIO21 pull-up and IMU timestamp scale. Stage-00 inventory and per-stage parts lists now include every staged fixture item.
- Rebuilt all seven profiles; 46 host tests and 38 native recorder-control cases pass. The Wokwi integrated matrix still refers to firmware 1.6 and was not repeated. Physical validation remains pending; the five other designs are unchanged.

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
