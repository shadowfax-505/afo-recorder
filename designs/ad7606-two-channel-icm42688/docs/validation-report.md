# Current validation — AD7606 / two EMG / ICM-42688-P

Project lead: Muttakin Rahman · updated 10 October 2026

Current recording firmware is **ad7606-2ch-1.7**: Source set **ad7606-2ch-1.7** (10 October 2026) moves the SD record queue to PSRAM and enlarges it from 2,048 to 20,480 records (about 0.244 s to 2.44 s), generates a random Wi-Fi password on each recorder instead of compiling one in, raises the live-metadata limit to 1,400 bytes, and adds IMU timestamp-scale checks. All seven 1.7 profiles compile and the native recorder-control cases pass again; **the Wokwi integrated runs below used the 1.6 image and have not been repeated for 1.7.**

The 1.6 firmware retained the ADC task wake-up and FIFO-burst timestamp corrections found during v1.5 integrated execution, and now rejects missing BUSY assertion/ignored CONVST before accepting stale ADC words. The [integrated verification report](integrated-verification.html) is the current evidence entrypoint. **All 18 current integrated cases pass within the documented models. Physical acceptance remains unperformed.**

| Evidence | Current result |
|---|---|
| Preserved v1.5 production firmware, FreeRTOS, FatFS and lwIP on Wokwi | Ten complete CLI/firmware passes; nominal firmware/file/UDP checks also pass with optional trace-download failure |
| v1.6 integrated firmware / protocol-fixture execution | All 18 current cases pass in the web editor; complete file/live decode and explicit fault reporting. [v1.5 exact tested source/image snapshot](../simulations/integrated-recorder/tested-source-1.5/manifest.json) is retained |
| Complete visible system | Two original nominal runs and an additional input-only pin-probe run pass; original recorder image and sensor-model C files preserved |
| Complete-scene digital pin capture | 10,041 conversions/reads; 128 clocks per read; 8 MHz clock; both 200 Hz interrupts. First two reads independently decoded from raw edges. [Partial derived waveform and limitations](digital-timing.html) |
| Independent saved-data comparison | 21,116 original record CRCs and CSV rows checked across known-DC and synthetic-waveform captures; enabled-channel identity, scaling, timing flags, final counters and saved/live byte parity pass. Eleven damaged-data cases rejected. [Interpretation and download](data-interpretation.html) |
| Current low-battery export | Both file and UDP dumps complete; earlier v1.5 partial capture remains historical |
| KiCad / independent pin comparison | Clean ERC/DRC; 390 pins and 22 GPIOs per profile compared without mismatches |
| Current v1.7 laboratory firmware | All seven profiles cross-compiled without warnings; not flashed and not rerun in Wokwi |
| Native actual ADC driver / IMU timing helper | 16 / eight groups pass |
| Native production recorder control | 38 cases pass across PCB and breadboard profiles |
| Host converter / live / legacy / firmware limits | 46 tests pass |
| Integrated evidence runner | 16 tests pass |
| Current behavioral ADC model | 12 native groups pass under address/undefined sanitizers; also executed by the current 18-case Wokwi web matrix and nominal complete-scene runs; electrical behavior remains modeled |
| Input-only virtual timing instrument | Ten native groups, including twelve injected fault variations, pass; actual browser capture uses the supplied C source; local WASI build separately passes |
| Captured timing audit | Nine auditor regression tests pass; current capture post-processing passes; no physical clock calibration |
| Laptop receiver / HTTP / live browser / archive | Two current v1.6 socket/API/browser/archive cases pass; preview/packet loss remains visible; no RF link |
| Actual C analog-to-file pipeline | 60 seconds, 480,000 EMG / 12,009 foot / 12,001 shank; 916/915 counter rollovers; correct codes; zero regressions or unexplained loss; pending foot packet counted |
| Analog surrogate | Two channels; 16 tolerance corners; 54 DC/loading cases; analytical response comparison passes |
| Queue capacity model | Four assumed one-hour writer cases pass; stall/throughput faults overflow explicitly. No firmware endurance or card measurement |
| QEMU timing experiment | Refusals exercised; nominal acquisition fails; not a qualified continuous-recording result |
| Native full-session waveform download | No new VCD retrieved; partial observer-derived edge CSV/VCD supplied with explicit coverage; clock idle polarity and physical setup/hold remain unqualified |
| Physical tests | None performed |

Read the [circuit audit](circuit-audit.html), [recording/recovery guide](recording-verification.html), [module qualification](module-qualification.md) and [short staged guide](lab-quickstart.html). Current manufacturing files remain engineering-prototype outputs; bench results and final review precede any order recommendation.

## Historical execution retained

The [seven earlier diagnostic Wokwi scenarios](virtual-verification.html) passed serial/VCD checks on their preserved tested image. Three hundred FreeRTOS join/lifecycle cycles also passed on an earlier v1.4 lifecycle image with stub peripherals. Both source/image histories are retained. Neither is a rerun of all current v1.6 profiles.

## Earlier assembly review — 28 September 2026

Fresh schematic-to-PCB parity, all-severity DRC and ERC passed. Assembly checks additionally verified unique insertion holes, named-net continuity, connector contacts and stage dependencies. The missing SD module ground lead at JP1.2 was added and checked. These checks establish topology, not physical SD operation.

Physical terminal maps are specified; remaining qualification is received-board inspection and measurement. Follow [bench/PCB differences](bench-pcb-differences.md) and the staged guide. Empty measured-results cells remain untested. Earlier report dates and binary hashes identify their own evidence and do not supersede the current integrated ledger.

## Breadboard handoff update — 3 October 2026

The [breadboard instructions](breadboard-refinements.html) now apply the current simulation findings to the fixed-two AD7606/ICM build. Stage cards and per-wire notes identify common CVA/CVB triggering, BUSY acceptance, full DOUTA frames, discarded startup reads, physical mode-2 checks, independent IMU timing and separate saved-file/wireless quality audits. The fixed-two stage no longer describes expandable ports. USB pin polarity and the printed attachment indicator are distinguished explicitly.

Fresh static checks pass: 184 wire rows match both CSV tables and the printable HTML; 17 firmware pin comparisons and 18 probe contacts match; all seven compiled profiles and current source hashes match their manifests; 30 checklist rows remain NOT TESTED. The independent breadboard connectivity check passes for all six existing layouts. The focused layout has 402 occupied holes, 24 GPIO checks and no disconnected named nets, shorted nets, duplicated holes or duplicated connector contacts. Electrical endpoints, PCB files, existing binary/source files, earlier ZIPs and the other five designs are preserved.

The [current breadboard lab kit](../breadboard/breadboard-lab-kit.zip) includes the six laboratory profiles, viewer, wire tables, converter and blank results sheets. Its [download receipt](../breadboard/breadboard-lab-kit.json) identifies the archive hash and 18 checked binary files. Simulator-only images and the PCB-specific recording image are excluded from this lab download. This update verifies instructions and artifact consistency; it adds no physical measurements or fresh execution of the laboratory binaries.
