# Changelog

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
