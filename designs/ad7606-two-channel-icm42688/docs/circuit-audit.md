# Circuit review: AD7606, two EMG inputs, ICM-42688-P

Project lead: Muttakin Rahman · Review: 30 September 2026

**The intended signal path is logically consistent, and fresh connectivity and software checks pass. This is not a fully verified recorder.** Seven actual-firmware Wokwi scenarios pass under the documented behavioral models; no physical recorder has been measured. Do not interpret the manufacturing exports as an order recommendation.

## What changed

| Finding | Correction | Evidence / remaining limit |
|---|---|---|
| Recording metadata described a RAW/VMID mixing circuit absent from the schematic | Describe the two buffered 3.3 kΩ/47 nF sections and single-ended output; add separate unplugged-bias metadata | No binary format change; firmware label is ad7606-2ch-1.4; converter/legacy tests pass |
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
| Host conversion / legacy / live reception | 40 tests pass |
| Software acquisition faults | 7 scenarios pass, including overflow, missing samples and interrupted file recovery |
| Firmware | Seven laboratory profiles available; three recording profiles rebuilt with ESP-IDF v5.4.2, four diagnostic images retained unchanged |
| ngspice | Both channels; 16 tolerance corners; 54 DC/loading cases; unplugged-bias case; transient/ideal quantization checks |
| Wokwi models | Both compile to WASM; native model unit tests pass |
| Wokwi ESP32 execution | **PASS, scoped to modeled digital behavior.** Seven actual ESP-IDF scenarios pass serial and VCD checks; see the [execution report](virtual-verification.md) |
| Recorder control logic | 38 native production-code cases pass; see the [recording report](recording-verification.html) |
| FreeRTOS task lifecycle | 300 actual ESP32-S3 Wokwi cycles pass; peripheral functions stubbed |
| Physical tests | None performed |

Evidence: [fresh checks](refinement-checks/connectivity.json), [breadboard](refinement-checks/breadboard-wiring.json), [host log](refinement-checks/host-tests.log), [builds](refinement-checks/firmware-builds.json), [analog results](../simulations/results/validation.json), [operating points](../simulations/results/operating-points.json), [Wokwi status](../simulations/wokwi/README.md). The broad historical reports remain available but do not supersede these limitations.

## EMG path and scaling

Each bare MyoWare RAW output feeds a 3.3 kΩ/47 nF low-pass section, a unity buffer, a second 3.3 kΩ/47 nF section, another unity buffer, then 100 Ω series resistance and 1 nF to ground at the ADC input. AD7606 V1/V2 are single-ended; their return pins are ground. V3–V8 and their returns are grounded on this fixed two-input PCB. All eight conversion words are clocked out; only V1 and V2 are exported as measurements.

A 1 MΩ resistor biases each unplugged RAW port toward the buffered 1.5 V midpoint. This bias is not an additive 1.5 V offset stage. `input_scale=1` and `input_midpoint_mv=0` correctly reconstruct connector RAW voltage. `unplugged_input_bias_mv=1500` describes the separate bias. Do not subtract 1.5 V in the converter under the existing field name. Mean removal for an analysis is a separate, documented processing step.

Each nominal RC pole is about 1026 Hz; the combined response is about −1.85 dB at 500 Hz and −3 dB near 660 Hz. The new ngspice response differs from the corresponding analytical model by at most 0.00263 dB below 20 kHz. Two 1 MHz closed-loop buffer surrogates include assumed 20 mV rail headroom and 1 Ω output resistance. They are **not manufacturer MCP6004 macromodels**. Neither that headroom nor the plotted clipping threshold is a guaranteed device specification. Noise, offset, bias current, PSRR, slew/current limits, supply coupling and protection-diode stress remain unvalidated.

The BAV199 orientation is ground → junction → 3V0A, with the junction at the first filter node. A diode drop can exceed an amplifier's permitted input overdrive; these clamps and the series resistor do not make the MyoWare connector tolerant of arbitrary ±5 V or ±10 V signals. Keep tests within the intended 0–3 V source domain. Validate overload/current behavior before claiming protection performance.

Original AD7606 ±5 V coding gives 152.588 µV/code. A 0–3 V sensor uses only about 30% of the total bipolar code range; “16-bit” describes the word, not 16 effective bits at the muscle sensor. Reference, gain, bias, ADC offset and analog noise require calibration. Synthetic waveforms do not establish physiological performance.

## ADC protocol and board differences

On the custom PCB: AVCC is 5V_ADC; VDRIVE is 3V3D. PAR/SER and STBY are high; RANGE and OS0–OS2 are low. CVA and CVB share GPIO11. GPIO8 monitors BUSY; GPIO9 resets. SPI2 uses GPIO12 SCLK, GPIO13 DOUTA and GPIO10 CS at 8 MHz, idle-high/falling-edge sampling (mode 2). A 1 µs CONVST pulse exceeds the specified 25 ns minimum. Eight words require 128 clocks (16 µs); maximum listed conversion time with oversampling off is 4.2 µs. This fits a 125 µs period arithmetically, but does not prove ESP32 task latency under SD/Wi-Fi load.

The AD7606 has no identification/configuration register readback and no sensor-frame CRC. File/container CRC protects transport/storage bytes only. Wrong range, mode or wiring can produce plausible data: apply two different known voltages and verify both codes, ground and polarity before recording sensors. A late conversion or unread previous result stops the driver instead of assigning a new timestamp to old data.

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

The firmware checks WHO_AM_I=0x47 and configuration readback, selects 200 Hz accel/gyro, ±16 g/±2000 dps, standard 16-byte FIFO records and 1 µs sensor timestamps. Byte order is big-endian. It detects full FIFO, invalid packet headers and missing/stale interrupt anchors. Sensor clocks are independent; FIFO timestamps wrap. ESP32 interrupt times and FIFO read windows are preserved, and reconstructed sample times remain explicitly uncertain. No claim of calibrated EMG-to-IMU alignment is made.

## Sources and release gate

Primary references: [ADI AD7606 Rev G, Tables 2–3 and serial-interface sections](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf), [TDK ICM-42688-P](https://www.invensense.tdk.com/en-us/products/6-axis/icm-42688-p), [MikroE carrier](https://www.mikroe.com/6dof-imu-14-click), [TI TPS60150](https://www.ti.com/product/TPS60150), [TI TPS63070](https://www.ti.com/product/TPS63070), [Microchip MCP6004](https://www.microchip.com/en-us/product/mcp6004), [Nexperia BAV199](https://assets.nexperia.com/documents/data-sheet/BAV199-Q.pdf), [Wokwi ESP32 support](https://docs.wokwi.com/guides/esp32), [Wokwi Chips API](https://docs.wokwi.com/chips-api/getting-started).

The specified virtual checks **pass under documented model assumptions and capture limits**. Physical gates include received-module qualification, power/startup/ripple, analog noise/clipping/crosstalk, cable integrity, actual 8 kHz timing, sustained SD/Wi-Fi recording, battery runtime and final PCB layout review. No board order or human-use approval follows from this report.

## Follow-up: verification safeguards and driver logic

Fifteen synthetic runner regression tests now reject stale files, partial windows, wrong sample rates/channel values and empty traces. Ten native C test groups also execute the production AD7606 driver against mocked timer, BUSY and SPI APIs, including late-read and unread-conversion faults. These are separate from the 40 host/converter tests. They do not emulate ESP32 concurrency or measure physical timing. See `simulations/driver-tests/` and `simulations/wokwi/tests/`. The [Wokwi execution report](virtual-verification.md) records the seven passing scenarios and capture limits.

## Execution-driven corrections

SPI mode is now initialized with a discarded read during RESET before the first measured conversion. A shared diagnostic fault latch stops all tasks after a worker error, preventing a subsequent plausible-looking window. Both changes are in the seven rebuilt profiles. The first measured frame and FIFO-overflow stop behavior pass Wokwi checks. Detailed results and the first-conversion waveform are in the [virtual verification report](virtual-verification.md).

## Recording firmware follow-up

Recording firmware ad7606-2ch-1.4 corrects worker handle lifetime, stops acquisition after a latched fault, attempts both IMU shutdowns and publishes the wireless END verdict after final filesystem checks. Thirty-eight native cases pass across the breadboard and PCB profiles. Read the [recording and recovery report](recording-verification.html) for the RTOS evidence and limits, stop reasons and the persistence caveat. Legacy binary decoding is unchanged. Board geometry, electrical connections and the five other setups are unchanged.
