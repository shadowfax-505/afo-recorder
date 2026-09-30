# Validation status

## Integrated AD7606 / two-channel / ICM verification — 1 October 2026

The [integrated report](../designs/ad7606-two-channel-icm42688/docs/integrated-verification.html) supersedes earlier current-firmware summaries for this configuration. Version `ad7606-2ch-1.5` fixes delayed ADC servicing and IMU timestamp regressions found during actual ESP-IDF execution. All seven laboratory profiles recompile; the fresh connection audit reports zero ERC/DRC violations and zero mismatches across 390 functional pins.

Ten integrated Wokwi cases completed with passing checks. The nominal run produced 10,041 EMG records with a complete file and no detected sample loss; its optional trace download failed after the firmware completed. Four cases were refused by the monthly cloud quota, and the low-battery run stopped correctly but did not finish exporting its UDP evidence. The full 16-case matrix has not passed. Storage uses a PSRAM block medium with real FatFS; controls and battery are fixture values; UDP uses loopback. These substitutions do not validate physical SDMMC, radio, power or battery performance.

Current v1.6 rejects ADC conversions whose BUSY signal never asserts. Local coverage includes 16 ADC driver groups, eight IMU clock groups, 38 recording-control cases, 40 converter/live/legacy tests, and a 60-second production-driver pipeline with 480,000 EMG records from repeated ngspice-derived signals. Sixteen integrated-runner tests, nine capture-timing tests and twelve independent ADC model groups pass. Two laptop replays pass real UDP, HTTP, browser and archive checks. All eighteen current v1.6 cloud cases remain unexecuted after one quota-refused attempt; earlier v1.5 captures do not establish v1.6 execution. Historical seven-case diagnostic and 300-cycle lifecycle results retain their original tested binaries and sources; they are not executions of the newly rebuilt images. Other five packages are unchanged by this focused refinement.

## Completed for the three MPU derivatives

- 27 firmware profiles cross-compiled: 7 fixed-two AD7606, 10 expandable AD7606 and 10 ADS131M04.
- Host suites: 47 tests fixed-two, 43 expandable AD7606, 43 ADS131M04. Includes legacy decoding and new MPU conversion/live/fault scenarios.
- Shared native firmware helpers tested for FIFO sizing, overflow, timestamp estimates, missed-interrupt/count mismatch and read races.
- Twenty-five synthetic ADC/MPU scenarios converted with plots: five fault modes across five supported ADC/channel configurations.
- Fresh ERC/DRC: zero reported violations and zero unconnected items for each MPU board. STEP, Gerber, drill, BOM, placement and assembly exports regenerated.
- Automated schematic/PCB/firmware/viewer comparisons passed: 390, 430 and 389 functional pins respectively. These checks do not validate purchased module header positions.
- Three MPU viewers exercised for stage selection, module/wire inspection and compact PCB view without captured JavaScript errors.
- Original ICM package files checked against saved hashes and unchanged.

See each package's validation report and raw test reports. Older baseline evidence is not a fresh physical validation of either family.

## Open gates

No hardware has been flashed or measured in this work. Supply/regulator and I²C pull-up behavior, physical carrier headers, timing jitter/drift, ADC accuracy/noise/crosstalk, cable reliability, full-card and interrupted-power behavior, sustained SD/Wi-Fi load, thermal performance and two-hour battery runtime remain unmeasured.

AD7606 header/serial-strap mapping remains a blocker to its physical wiring. The DevKit SD command assignment is now GPIO47 in breadboard firmware, with physical verification still pending. GY-521 body/header geometry remains illustrative. ADS131M04 carrier availability is unresolved. Research-ready, clinical-performance and safety claims are not established.

## SD correction checks — 2026-09-27

All 26 recording profiles compiled with ESP-IDF v5.4.2. Twelve native pin/metadata configurations, six viewer endpoint/zoom/stage checks and all six host regression suites passed. The breadboard now uses GPIO47 for SD CMD; custom PCB GPIO38 and its CAD/manufacturing exports are unchanged. Six ZIPs were refreshed. These checks do not replace stage-7 hardware testing.

## Expanded wiring viewer

Six viewers now display 106–122 individual named-terminal wires per setup, plus the existing breadboard jumpers and exact SD leads. Net coverage, firmware GPIO matching, subsystem presence, endpoint selection and stage filtering passed. No firmware/CAD changes or new physical measurements were made. Physical module maps, fan-out hole allocation and USB VBUS access are still pending; see wiring-status.md.

## Photo header maps

Five affected viewers passed connection presence, photo-evidence labeling and zoom checks. Supplied product photos now identify the pictured AD7606 and GY-521 header order. AD7606 serial data-pin grounds were completed in the harness. Physical electrical validation remains pending; mode straps must be verified before fitting serial-mode terminations. All five affected ZIPs were refreshed.
