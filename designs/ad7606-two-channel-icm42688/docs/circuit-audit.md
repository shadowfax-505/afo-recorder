# Circuit review: AD7606, two EMG inputs, ICM-42688-P

Project lead: Muttakin Rahman · Review: 1 October 2026

**The intended signal path is logically consistent, and current circuit/software checks pass. All 18 current v1.6 integrated cases pass in Wokwi with documented substitutes.** The [integrated report](integrated-verification.html) includes complete exports, explicit wireless gaps, preserved historical failures and the unqualified QEMU timing experiment. No physical recorder has been measured; manufacturing files remain engineering prototypes.

## What changed

| Finding | Correction | Evidence / remaining limit |
|---|---|---|
| Recording metadata described a RAW/VMID mixing circuit absent from the schematic | Describe the two buffered 3.3 kΩ/47 nF sections and single-ended output; add separate unplugged-bias metadata | No binary format change; current recording label is ad7606-2ch-1.6; converter/legacy tests pass |
| ADC diagnostic could wait indefinitely for BUSY | Fail explicitly after 100 ms without a falling edge | Cross-compiled; stuck/delayed BUSY faults verified in Wokwi |
| ADC timer could issue later triggers after a latched timing fault | Suppress triggers until stream restart | Source review; real interrupt latency still unmeasured |
| Diagnostics printed while acquisition remained active and polled IMUs in the ADC reader | Use bounded measurement windows; stop ADC for reporting; separate lower-priority FIFO service | Diagnostic output is discontinuous by design, not an endurance recording |
| Recorder could fault before the second IMU produced its first interrupt | Allow up to 100 ms for the first interrupt before draining that FIFO | Fixes the startup race; stale interrupts still trigger a fault |
| Analog model limitation mentioned an unrelated sinc3 response | Correct limitation for original AD7606, oversampling off | Does not model the ADC's internal analog filter |
| Custom IMU model could consume a prefetched FIFO byte | Consume only transferred bytes; distinguish FIFO reads from count-register reads | Native model test verifies no extra byte loss |

## Circuit traced

The authoritative source remains `design/circuit-spec.json`. `design/audit_connections.py` exports a fresh KiCad XML netlist and independently reads the PCB with pcbnew. It compares every connected spec pin directly against both; it preprocesses both firmware GPIO profiles instead of trusting a stale viewer export.

| Check | Result |
|---|---|
| KiCad ERC / DRC | 0 violations / 0 violations; no unconnected items |
| Connected schematic and actual PCB pads | 390 compared; 0 mismatches |
| Firmware GPIOs | 22 per profile; 0 mismatches |
| Breadboard topology | 184 wires, 402 occupied holes, 24 GPIO endpoint checks; 0 named-net splits, shorts, duplicate holes or connector contacts |
| Host conversion / legacy / live reception / firmware limits | 47 tests pass |
| Software acquisition faults | 7 scenarios pass, including overflow, missing samples and interrupted file recovery |
| Firmware | All nine v1.12 laboratory profiles (including two IMU-only bench diagnostics) recompiled with ESP-IDF v5.4.2 (32/30 µs IMU ticks, PSRAM record queue, per-device Wi-Fi password, IMU timestamp-scale checks, AN-1091 STBY sequence on the PCB, Wi-Fi preview session announced before data); all 18 web cases pass on the 1.12 image |
| ngspice | Both channels; 16 tolerance corners; 54 DC/loading cases; unplugged-bias case; transient/ideal quantization checks |
| Wokwi models | Both compile to WASM; native model unit tests pass |
| Preserved v1.5 integrated Wokwi execution | Ten complete CLI/firmware passes; nominal firmware/file/UDP passes with optional trace failure; battery partial; four cases unexecuted due to quota. [Tested source/image snapshot](../simulations/integrated-recorder/tested-source-1.5/manifest.json) |
| v1.6 integrated cloud execution (not repeated for 1.7) | All 18 current cases pass in the web editor; complete converter/decoder checks. Preserved v1.5 outcomes are separate |
| Historical diagnostic Wokwi execution | Seven cases passed on the preserved earlier image; [source/image snapshot](../simulations/wokwi/tested-diagnostic-20260930/manifest.json) |
| Native driver/timing logic | 16 current ADC groups and nine IMU timestamp-helper groups pass (rerun with ASan/UBSan for 1.8) |
| Integrated evidence runner | 16 tests pass; partial/quota evidence is not counted as passed execution |
| Current behavioral ADC model | 12 independent native groups pass with address/undefined sanitizers; no Wokwi runtime |
| Native analog-to-file pipeline | 60 seconds: 480,000 EMG, 12,009 foot and 12,001 shank; 916/915 counter rollovers; no unexplained loss; pending FIFO data counted |
| Captured timing audit | Nine tests pass on preserved v1.5 captures; both modeled IMUs 200 Hz; explicit 55,001 µs startup estimate offset |
| Laptop receiver/API/browser replay | Two real loopback-socket cases pass on preserved v1.5 datagrams; packet gaps and absent END retained |
| Recorder control logic | 38 native production-code cases pass; see the [recording report](recording-verification.html) |
| Historical FreeRTOS task lifecycle | 300 cycles passed on the preserved earlier image; peripheral functions stubbed. This is not a current-image rerun |
| Physical tests | None performed |

Evidence: [fresh checks](refinement-checks/connectivity.json), [breadboard](refinement-checks/breadboard-wiring.json), [host log](refinement-checks/host-tests.log), [builds](refinement-checks/firmware-builds.json), [analog results](../simulations/results/validation.json), [operating points](../simulations/results/operating-points.json), [Wokwi status](../simulations/wokwi/README.md). The broad historical reports remain available but do not supersede these limitations.

## EMG path and scaling

Each bare MyoWare RAW output feeds a 3.3 kΩ/47 nF low-pass section, a unity buffer, a second 3.3 kΩ/47 nF section, another unity buffer, then 100 Ω series resistance and 1 nF to ground at the ADC input. AD7606 V1/V2 are single-ended; their return pins are ground. V3–V8 and their returns are grounded on this fixed two-input PCB. All eight conversion words are clocked out; only V1 and V2 are exported as measurements.

A 1 MΩ resistor biases each unplugged RAW port toward the buffered 1.5 V midpoint. This bias is not an additive 1.5 V offset stage. `input_scale=1` and `input_midpoint_mv=0` correctly reconstruct connector RAW voltage. `unplugged_input_bias_mv=1500` describes the separate bias. Do not subtract 1.5 V in the converter under the existing field name. Mean removal for an analysis is a separate, documented processing step.

Each nominal RC pole is about 1026 Hz; the combined response is about −1.85 dB at 500 Hz and −3 dB near 660 Hz. The new ngspice response differs from the corresponding analytical model by at most 0.00263 dB below 20 kHz. Two 1 MHz closed-loop buffer surrogates include assumed 20 mV rail headroom and 1 Ω output resistance. They are **not manufacturer MCP6004 macromodels**. Neither that headroom nor the plotted clipping threshold is a guaranteed device specification. Noise, offset, bias current, PSRR, slew/current limits, supply coupling and protection-diode stress remain unvalidated.

The BAV199 orientation is ground → junction → 3V0A, with the junction at the first filter node. A diode drop can exceed an amplifier's permitted input overdrive; these clamps and the series resistor do not make the MyoWare connector tolerant of arbitrary ±5 V or ±10 V signals. Keep tests within the intended 0–3 V source domain. Validate overload/current behavior before claiming protection performance.

Original AD7606 ±5 V coding gives 152.588 µV/code. A 0–3 V sensor uses only about 30% of the total bipolar code range; “16-bit” describes the word, not 16 effective bits at the muscle sensor. Reference, gain, bias, ADC offset and analog noise require calibration. Synthetic waveforms do not establish physiological performance.

## ADC protocol and board differences

On the custom PCB: AVCC is 5V_ADC; VDRIVE is 3V3D. PAR/SER is high; STBY is driven by GPIO14 with a 100 kΩ pull-down (see the supply-ramp section below); RANGE and OS0–OS2 are low. CVA and CVB share GPIO11. GPIO8 monitors BUSY; GPIO9 resets. SPI2 uses GPIO12 SCLK, GPIO13 DOUTA and GPIO10 CS at 8 MHz, idle-high/falling-edge sampling (mode 2). A 1 µs CONVST pulse exceeds the specified 25 ns minimum. Eight words require 128 clocks (16 µs); maximum listed conversion time with oversampling off is 4.2 µs. This fits a 125 µs period arithmetically, but does not prove ESP32 task latency under SD/Wi-Fi load.

The AD7606 has no identification/configuration register readback and no sensor-frame CRC. File/container CRC protects transport/storage bytes only. Wrong range, mode or wiring can produce plausible data: apply two different known voltages and verify both codes, ground and polarity before recording sensors. A late conversion or unread previous result stops the driver instead of assigning a new timestamp to old data. In the current recording build, the conversion timer timestamps and wakes the ADC task directly; the task waits for BUSY to clear with an 80 µs deadline. This avoids the delayed falling-BUSY interrupt wake-up exposed by integrated execution. BUSY remains connected and monitored; ADC diagnostic windows use their own interrupt path.

The received HW-AD7606-F4/RBD-3184 module's labelled header is documented, but a photograph cannot prove its serial strap, VIO routing, reference choice or component substitutions. Verify the module electrically. The single-chip PCB does not reproduce undocumented breakout-board internals. See [bench/PCB differences](bench-pcb-differences.md) and [module qualification](module-qualification.md).

## Power, reference and controls

- A protected single-cell pack enters through the reverse-polarity P-channel MOSFET. Its body-diode orientation allows the intended initial feed; its gate is referenced to ground. Reverse-polarity behavior and off-state leakage still need low-energy bench testing.
- TPS63070 feedback 316 kΩ/100 kΩ gives nominal 3.328 V using its 0.8 V reference. Local inductor and capacitor loops belong on the PCB. Breadboard regulator modules validate rail behavior, not these switching loops.
- TPS7A2030 derives 3V0A. Verify dropout margin, stability and ripple with both MyoWare sensors and buffers connected, including radio/SD load steps.
- TPS60150 generates the ADC rail. Its conservative low-input capability is 50 mA; original AD7606 maximum listed operating total is 27 mA, leaving nominal current margin. This arithmetic does not validate startup charging, capacitor derating, ripple or thermal behavior. Verify AVCC remains 4.75–5.25 V. Do not assume a breakout's additional load equals bare-chip current.
- AD7606 REGCAP nodes each have 1 µF to ground; REFIN/REFOUT has 10 µF; REFCAPA/B are joined and have 10 µF. They are decoupling/reference nodes, not general-purpose supply outputs. The selected capacitors' voltage rating is adequate for the nominal rails; effective capacitance after DC bias, placement and tolerances needs assembly review and measurement.
- USB VBUS is sense-only. The 100 kΩ/1 MΩ gate network drives a 2N7002; a 10 kΩ pull-up produces active-low GPIO21 detection. VBUS has no intentional power-feed path into the battery/digital rail. Ground, data and ESD connections are not galvanic isolation. Firmware refuses recording while USB is detected.
- The development-board SD command is GPIO47; the custom PCB uses GPIO38. This documented exception avoids the DevKit's RGB LED load. Use the matching build. CLK is GPIO39 and D0 is GPIO40; selected adapter contacts and return lead are checked separately.

## IMU path and timing

Use the selected MIKROE-4237 carrier with JP2–JP4 in SPI position (pads 1–2), 3.3 V power and the specified mikroBUS header orientation. SPI3 is shared on GPIO4/5/6 (MOSI/MISO/SCLK); separate CS GPIO7/15 and INT1 GPIO16/17 identify foot/shank. Verify carrier solder bridges, supply and connector orientation on the received parts.

The firmware checks WHO_AM_I=0x47 and configuration readback, selects 200 Hz accel/gyro, ±16 g/±2000 dps, standard 16-byte FIFO records and sensor timestamps in 1 µs mode, whose ticks last 32/30 µs on the ICM-42688 (applied from firmware 1.8). Byte order is big-endian. It detects full FIFO, invalid packet headers and missing/stale interrupt anchors. Sensor clocks are independent; FIFO timestamps wrap. ESP32 interrupt times and FIFO read windows are preserved. The first FIFO burst anchors an estimate; later samples advance by the sensor timestamp counter delta instead of re-anchoring every burst. Ambiguous counter/read intervals are rejected. Reconstructed sample times remain explicitly uncertain. No claim of calibrated EMG-to-IMU alignment is made.

## Sources and release gate

Primary references: [ADI AD7606 Rev G, Tables 2–3 and serial-interface sections](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf), [TDK ICM-42688-P](https://www.invensense.tdk.com/en-us/products/6-axis/icm-42688-p), [MikroE carrier](https://www.mikroe.com/6dof-imu-14-click), [TI TPS60150](https://www.ti.com/product/TPS60150), [TI TPS63070](https://www.ti.com/product/TPS63070), [Microchip MCP6004](https://www.microchip.com/en-us/product/mcp6004), [Nexperia BAV199](https://assets.nexperia.com/documents/data-sheet/BAV199-Q.pdf), [Wokwi ESP32 support](https://docs.wokwi.com/guides/esp32), [Wokwi Chips API](https://docs.wokwi.com/chips-api/getting-started).

Completed checks pass within their stated scope. **The current whole-system case matrix passes within its documented model/substitution limits**; see the [case ledger](integrated-verification.html). Physical gates include received-module qualification, power/startup/ripple, analog noise/clipping/crosstalk, cable integrity, actual 8 kHz timing, sustained SD/Wi-Fi recording, battery runtime and final PCB layout review. No board order or human-use approval follows from this report.

## Follow-up: verification safeguards and driver logic

Fifteen synthetic runner regression tests now reject stale files, partial windows, wrong sample rates/channel values and empty traces. Sixteen native C test groups also execute the production AD7606 driver against mocked timer, BUSY and SPI APIs, including late-read and unread-conversion faults, direct timer wake-up, missing BUSY assertion, ignored CONVST and the bounded BUSY wait. Eight additional groups check the production IMU timestamp helper. These are separate from the 40 host/converter tests. They do not emulate ESP32 concurrency or measure physical timing. See `simulations/driver-tests/` and `simulations/wokwi/tests/`. The [historical Wokwi report](virtual-verification.md) records the seven earlier diagnostic scenarios and capture limits. The [current integrated report](integrated-verification.html) records actual recorder/FatFS/UDP execution and its scope.

## Execution-driven corrections

SPI mode is now initialized with a discarded read during RESET before the first measured conversion. A shared diagnostic fault latch stops all tasks after a worker error, preventing a subsequent plausible-looking window. Both changes remain in the seven current recompiled profiles. The first measured frame and FIFO-overflow stop behavior passed the earlier diagnostic image, and current integrated known-code/overflow checks also pass. Detailed results and the first-conversion waveform are in the [virtual verification report](virtual-verification.md).

## Recording firmware follow-up

The v1.4 recording correction, retained in ad7606-2ch-1.6, fixes worker handle lifetime, stops acquisition after a latched fault, attempts both IMU shutdowns and publishes the wireless END verdict after final filesystem checks. Thirty-eight native cases pass across the breadboard and PCB profiles. Read the [recording and recovery report](recording-verification.html) for the RTOS evidence and limits, stop reasons and the persistence caveat. Legacy binary decoding is unchanged. Board geometry, electrical connections and the five other setups are unchanged.

## Integrated acquisition follow-up

Preserved v1.5 execution corrected a delayed ADC task wake-up and FIFO-burst timestamp regressions. Sixteen current native ADC groups, eight timing-helper groups, 38 native recorder cases and 40 host tests pass. Preserved v1.5 Wokwi nominal SD-file and UDP data have zero timestamp regressions and no detected saved-sample loss; deliberate faults remain explicit. The [integrated verification report](integrated-verification.html) preserves unsuccessful attempts, the partial battery export, quota refusals and exact source/image hashes.

## Missing conversion acknowledgement — current v1.6

The driver now requires BUSY high at the end of the 1 µs CONVST pulse, before making the frame pending. A missing assertion indicates a disconnected/stuck-low BUSY line or ignored conversion and latches a timing fault instead of reading stale words. This follows the AD7606 Rev G 45 ns maximum BUSY assertion and 3.45 µs minimum conversion timing. Sixteen native driver groups and the local C pipeline pass with the new safeguard. The current v1.6 web matrix executes all three ADC handshake fault cases and rejects them with an ADC error and zero EMG; its [v1.5 baseline snapshot](../simulations/integrated-recorder/tested-source-1.5/manifest.json) is retained separately.

## Current full-system execution

All 18 v1.6 web cases pass. A startup stack-allocation correction is included in the rebuilt images. Current laptop replays retain one nominal preview drop and 158 deliberately missing packets visibly, with exact archived measurement bytes. QEMU establishes additional refusal behavior but fails nominal timing qualification; it is not counted as continuous-acquisition evidence. Current web byte/capture timing checks are distinct from the preserved diagnostic VCDs. See the [integrated report](integrated-verification.html).

## Official AD7606 datasheet cross-check — 11 October 2026

The project lead supplied ADI's AD7606/AD7606-6/AD7606-4 data sheet, **Rev. G (2/2025)**. It is used as a local reference only and is not redistributed. Every AD7606 pin in the PCB netlist (`hardware/main/netlist.xml`, U2) and every firmware timing value were compared with it.

| Item | Data sheet (Rev. G) | This design | Result |
|---|---|---|---|
| Conversion time, oversampling off | tCONV 3.45 / 4 / **4.2 µs** min/typ/max (Table 3) | Documents use 4.2 µs max | Confirmed; the 4.15 µs recollection was wrong |
| CONVST to BUSY high | t1 ≤ 40 ns (45 ns at 0.3/0.7 VDRIVE levels) | BUSY sampled 1 µs after CONVST rises | Pass |
| CONVST high/low pulse | t3, t2 ≥ 25 ns | 1 µs high, ≈124 µs low | Pass |
| CONVST A to CONVST B | t5 ≤ 0.5 ms | Both on GPIO11 | Pass (simultaneous) |
| RESET | tRESET ≥ 50 ns; RESET low to CONVST ≥ 25 ns (t7); reset required after power-up | 2 µs pulse at start-up, 10 ms before first conversion | Pass |
| Read timing | Read after BUSY falls (t4 ≥ 0); CONVST ignored while BUSY is high | Driver waits for BUSY low (80 µs deadline); faults if BUSY is still high at the next trigger | Pass |
| Serial clock at VDRIVE 3.3 V | fSCLK ≤ 17 MHz (15 MHz at 0.3/0.7 levels) | 8 MHz | Pass |
| Serial data edges | MSB valid at first SCLK falling edge after CS (t18 ≤ 23 ns); later bits change on rising edge, valid ≤ 26 ns (t19), hold ≥ 7 ns (t22) | SPI mode 2 (idle high, sample on falling edge); 62.5 ns half period; IO-MUX pins GPIO10/12/13 | Pass, ≥ 36 ns setup margin before the ESP32 input delay |
| Single-line read | DOUTA carries V1…V8 in 128 SCLK; unused DOUTB left unconnected | 128-bit read on DOUTA; DOUTB unconnected | Pass |
| Interface straps (Table 8) | PAR/SER/BYTE SEL = 1, DB15/BYTE SEL = 0; DB[15:9], DB[6:0] and DB14/HBEN to ground in serial mode | Pin 6 to 3V3D; pins 16–22 and 27–33 to GND | Pass |
| Other straps | OS[2:0] = 000 (no oversampling); RANGE low = ±5 V; STBY high = normal; REF SELECT high = internal reference; unused inputs to AGND | Pins 3–5 GND, 8 GND, 7 to 3V3D, 34 to 3V3D, V3–V8 and all VxGND to GND | Pass; firmware full scale 5000 mV matches ±5 V |
| Decoupling (Fig. 43) | 100 nF per AVCC pin (pins 37/38 may share) plus 10 µF; 10 µF on REFIN/REFOUT; REFCAPA+REFCAPB shorted with 10 µF; 1 µF per REGCAP | C200–C203 (3 × 100 nF + 10 µF), C207 10 µF, C208 10 µF on the shorted pair, C205/C206 1 µF | Pass |
| Supply ranges | AVCC 4.75–5.25 V; VDRIVE 2.3–5.25 V, recommended < 3.6 V | TPS60150 5 V (4.8–5.2 V); VDRIVE 3.3 V | Pass |
| Analog input | 1 MΩ input; ±5 V range LSB 152.58 µV; −3 dB 15 kHz, group delay 15 µs | 100 Ω/1 nF after the 660 Hz board filter | Pass; see the offset note below |

**Series resistor without a matching VxGND resistor (Fig. 36).** The data sheet notes an offset when only Vx has series resistance. The input current (2.5 µA at 5 V, Fig. 31, so about 1.5 µA at 3 V) through R104/R114 (100 Ω) gives at most about 0.25 mV, under 2 LSB. That is well inside the bipolar-zero error (±12 LSB max at ±5 V), and the stage-3 two-point DC calibration removes it. No change is needed.

**Supply ramp order: implemented on 12 October 2026 (PCB and firmware 1.11).** AVCC (5V_ADC) is made from 3V3D by the TPS60150 charge pump. Its enable is tied to its input, its output is disconnected while it is off, and it soft-starts in about 150 µs (TI data sheet). So VDRIVE (3V3D) is always present before AVCC. Table 4 limits VDRIVE to AVCC + 0.3 V, and ADI application note **AN-1091** covers delayed AVCC/VDRIVE ramps: hold STBY and RANGE low until both supplies are up, then raise STBY, wait tWAKE-UP SHUTDOWN (30 ms with the internal reference) and apply RESET. The project lead approved the following change:

| Item | Change | Check |
|---|---|---|
| STBY control | AD7606 pin 7 moved from 3V3D to new net ADC_STBY, driven by ESP32 GPIO14 (module pad 22, not a strapping pin). R70 (100 kΩ, 0603) pulls it low, so with RANGE low the ADC stays in full shutdown until the firmware releases it | Schematic, netlist and every PCB pad agree (connection audit: 395 pins, PCB GPIO map 23 entries) |
| Ramp clamp | D30, a BAT760 Schottky (SOD-323), from 3V3D (anode) to 5V_ADC (cathode). It pre-charges AVCC while 3V3D rises and is reverse-biased once the pump reaches 5 V | BAT760 VF max 270 mV at 10 mA and 350 mV at 100 mA; reverse leakage 5 µA typ at 5 V (Nexperia data sheet) |
| Firmware 1.11 | PCB builds drive STBY high once per boot, wait 30 ms, then pulse RESET. Breadboard builds do not touch GPIO14 | Native driver test: STBY rises at least 30 ms before the first RESET (17 groups, ASan/UBSan); nine profiles rebuilt |
| Layout | STBY: 49 mm of 0.15 mm track (F.Cu, In2.Cu, B.Cu) with 7 vias, entering pin 7 from inside the package. Pin 8 (RANGE, tied to GND, no current) used to reach ground through a 0.2 mm track around the inside of pins 4–8 that blocked pin 7. That track and the pin 6–7 stub were removed; pin 8 now reaches the In1 ground plane through its own 0.15 mm track and via. D30's anode reaches the 3V3D pour on In2 through a via; its cathode joins 5V_ADC copper directly | KiCad DRC with the project rules: 0 violations, 0 unconnected; ERC: 0. Schematic parity matches the earlier board apart from the existing missing-MPN-field note on the two new footprints |

Margins and limits: the TPS63070 soft-starts 3V3D in roughly 0.4 ms. Charging the ~12.5 µF on 5V_ADC through D30 then takes about 0.1 A, so VDRIVE − AVCC stays near 0.30–0.35 V for well under a millisecond. Without the diode it can be the full 3.3 V. That is still at, not comfortably below, the 0.3 V absolute-maximum figure, which is why the firmware also follows the AN-1091 sequence. The TI data sheet does not describe starting the TPS60150 into a pre-charged output. The new copper was routed by a script against the exported board geometry and accepted only after KiCad's DRC.

Remaining checks:
- On the first assembled PCB, record 3V3D, 5V_ADC and STBY at power-up on the oscilloscope.
- Confirm the TPS60150 starts normally with the pre-charged output.
- Confirm BAT760 availability before ordering.
- Review the new copper in the final layout review.

The breadboard uses separate 5 V and 3.3 V regulator modules and the ADC module's own STBY tie. Its stage 3 still records the power-up order of the two rails.
