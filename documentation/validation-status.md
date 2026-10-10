# Validation status

## Integrated AD7606 / two-channel / ICM verification — 1 October 2026

The [current integrated report](../designs/ad7606-two-channel-icm42688/docs/integrated-verification.html) records **18/18 v1.6 web-simulator cases passing** actual ESP-IDF recorder, ADC/IMU, FreeRTOS, FatFS and UDP execution with documented substitutes. Current laboratory firmware 1.7 compiles and passes host and native recorder tests but has not been rerun in Wokwi. Complete exports pass the real converter and live decoder. Current real-socket/API/browser/archive replays retain preview drops and packet gaps accurately. The nominal saved recording has no detected sample loss.

All seven laboratory profiles compile. Clean ERC/DRC and independent comparison cover 390 functional pins and 22 GPIOs per profile. Separate coverage includes 16 ADC groups, eight IMU clock groups, 38 recorder-control cases, 40 host/legacy tests, 16 integrated-runner tests, nine timing tests, twelve model groups and the 60-second 480,000-frame C pipeline. QEMU’s nominal timing qualification fails and remains labeled unqualified. Earlier seven-case diagnostic and 300-cycle lifecycle evidence retains its exact tested images; it is not execution of every newly rebuilt profile. No current downloaded VCD or physical performance is claimed. The other five designs are unchanged.

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

AD7606 header order is documented from photographs; the received board’s serial strap and electrical levels still require physical qualification. The DevKit SD command assignment is now GPIO47 in breadboard firmware, with physical verification still pending. GY-521 body/header geometry remains illustrative. ADS131M04 carrier availability is unresolved. Research-ready, clinical-performance and safety claims are not established.

## SD correction checks — 2026-09-27

All 26 recording profiles compiled with ESP-IDF v5.4.2. Twelve native pin/metadata configurations, six viewer endpoint/zoom/stage checks and all six host regression suites passed. The breadboard now uses GPIO47 for SD CMD; custom PCB GPIO38 and its CAD/manufacturing exports are unchanged. Six ZIPs were refreshed. These checks do not replace stage-7 hardware testing.

## Expanded wiring viewer

Six viewers now display 106–122 individual named-terminal wires per setup, plus the existing breadboard jumpers and exact SD leads. Net coverage, firmware GPIO matching, subsystem presence, endpoint selection and stage filtering passed. No firmware/CAD changes or new physical measurements were made. Physical module maps, fan-out hole allocation and USB VBUS access are still pending; see wiring-status.md.

## Photo header maps

Five affected viewers passed connection presence, photo-evidence labeling and zoom checks. Supplied product photos now identify the pictured AD7606 and GY-521 header order. AD7606 serial data-pin grounds were completed in the harness. Physical electrical validation remains pending; mode straps must be verified before fitting serial-mode terminations. All five affected ZIPs were refreshed.
