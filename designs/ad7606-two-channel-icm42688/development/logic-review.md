# Logic review and remaining gates

Review date: 4 October 2026. Scope: fixed-two AD7606 / ICM-42688-P breadboard and corresponding PCB. This is a review of the available design, code and evidence, not certification of every possible failure or a measured device. Physical results remain NOT TESTED.

## Findings that change the assembly workflow

1. **IMU diagnostics depend on a working ADC.** `firmware/main/diagnostic.c` initializes and runs the ADC before the IMU stage. Stage 6 now explicitly retains it. Controller diagnostics branch before ADC initialization, so stage 2 needs neither ADC, IMUs, SD nor Wi-Fi.
2. **Electrical voltage targets were inconsistent between documents.** Use 3.23-3.43 V for the digital rail and VIO project screen, 2.94-3.06 V for the analog rail, and 4.80-5.20 V for the ADC rail. AD7606 AVCC operating bounds remain 4.75-5.25 V; those wider bounds are not the preferred build target. Record uncertainty and transient peaks. Midpoint must be 0.49-0.51 times the measured analog supply; an absolute 1.47-1.53 V check is only a nominal 3.00 V shortcut.
3. **A test window is not an endurance run.** Diagnostics intentionally pause triggering to print. Measure cadence within windows; use recording firmware for uninterrupted timing and storage tests. Do not divide diagnostic counts by wall time including print pauses.
4. **ADC range does not protect the external buffer.** AD7606 accepts bipolar inputs, but this 3 V MCP600x circuit does not. Keep test inputs within 0.1-2.9 V. BAV199 clamps and series resistance do not establish safe arbitrary overvoltage behavior.
5. **Two sensor clocks are not one clock.** Retain raw ICM counters, IRQ anchors, read intervals and timing flags. Independent starts and reconstructed times require a measured synchronization error budget before cross-signal onset or gait-phase claims.
6. **A valid container is not valid physiology.** CRC verifies stored bytes. It cannot detect an electrode on the wrong muscle, movement artifact, analog clipping upstream, incorrect normalization or inaccurate event labels.

## Coverage and test ownership

| Domain | Logical requirement / available evidence | Required next evidence |
|---|---|---|
| Power and return paths | Separate 3.3 V digital, 3 V analog and 5 V ADC rails; common return; local bypassing. PCB and breadboard supply implementations differ. | Stage 1 startup, ripple, dummy loads; repeat under stages 2-9 load. |
| Controller / reset / USB | GPIO21 active-low USB detection; diagnostic attachment allowed; recorder must inhibit/stop. SD CMD differs: breadboard 47, PCB 38. | Stage 2 reset/control measurements; stage 7 actual recorder interlock. |
| AD7606 reference / straps | Original AD7606 serial mode, VDRIVE 3.3 V, range +/-5 V, oversampling off; reference and bypass circuit in existing audit. Seller photograph cannot qualify a received board. | Stage 3 continuity, voltage and logic-level evidence before ESP32 wires. |
| Conversion / read | GPIO11 drives CVA/CVB together, BUSY GPIO8, reset 9, CS10, SCLK12, DOUTA13. Read all eight 16-bit words, retain first two. | Scope/logic analyzer at actual pins, known DC and swapped identity tests. |
| Analog channels | Two buffered 3.3 kohm/47 nF sections each, 100 ohm/1 nF output, 1 Mohm unplugged bias to buffered midpoint. | Stages 4/5 response, offsets, clipping, noise, crosstalk and settling. |
| IMU paths | Shared SPI 4/5/6; foot CS7/INT16; shank CS15/INT17. Carrier jumpers must select SPI. FIFO and independent clocks preserved. | Stage 6 six-face tests, independent movements, IRQs, rate, cable tests; stage 8 load regression. |
| Storage | Original versioned records, counters, CRC and stop status; 2048-entry producer/consumer queue. | Stage 7 real SDMMC stalls, endurance, fault recovery and sync/close behavior. |
| Wireless | Best-effort preview distinct from original SD stream; gaps must remain visible. | Stage 8 both raw archives and intentional disconnects. |
| Battery / mechanics | Protected pack and firmware thresholds do not certify runtime or mounting. | Stage 9 measured runtime; stage 10 AFO clearance, retention and artifacts. |
| Research interpretation | Raw voltages and inertial signals require labels, calibration and an uncertainty budget. | Stage 10 study protocol, synchronized reference and repeatability pilot. |

The existing circuit audit contains the component-level reference/decoupling, protection, regulator and package review. The fresh connectivity report in `../docs/refinement-checks/connectivity.json` compares actual schematic nodes, PCB pads and preprocessed firmware pins. Matching nets and clean ERC/DRC cannot validate a wrong shared specification or a physical module's internal wiring. Read both reports together.

## Quantitative checks

- AD7606 signed conversion at +/-5 V: `volts = code * 5 / 32768`. One code is 152.588 microvolts at the ADC input. A nominal 0-3 V span occupies about 19,661 codes (14.26 ideal bits of span), not 16 effective bits of muscle measurement. This is not a measured ENOB claim.
- The two external RC poles are about 1026 Hz each. Combined nominal gain at 500 Hz is about -1.85 dB; at 4 kHz about -24.2 dB. This is finite attenuation, not a brick-wall antialias filter. The MyoWare and ADC add their own response; measure the combined path and retain filter settings when interpreting frequency features.
- Nominal ADC conversion maximum 4.2 us plus 128/8 MHz = 16 us serial transfer leaves about 104.8 us of a 125 us period before software overhead. This arithmetic is a feasibility check, not a real-time scheduling guarantee. The 80 us BUSY deadline is fault handling, not acceptable nominal conversion latency.
- With 64-byte records and nominal 8,000 EMG + 400 IMU records/s, payload is 537,600 bytes/s, 1.93536 GB/hour, 3.87072 GB/two hours, plus metadata/status/END. Reserve additional space; do not size cards to this minimum. Firmware limits one session to two hours. File-system limits and final flush still need real-media tests.
- 2,048 queue entries cover about 0.244 s at 8,400 records/s if initially empty. Available margin is smaller when already occupied. This is not a guaranteed tolerated SD stall. Inspect overflow and actual occupancy/stall behavior.
- At 200 Hz, samples are 5 ms apart. Accurate sub-millisecond EMG samples do not make 200 Hz motion labels sub-millisecond accurate. Event estimation, interpolation and reference alignment require separate validation.

## Research decisions before participant collection

Specify primary outcome first: for example TA activation timing relative to independently validated gait events, or normalized TA/medial-gastrocnemius coactivation under two AFO conditions. Define smallest meaningful effect and allowable timing/noise error from that outcome. Set exclusion rules before looking at outcomes. The provisional -40 dB electronic crosstalk screen does not establish physiological separation between muscles.

Do not treat relative IMU orientations as a validated ankle angle without sensor-to-segment calibration, alignment, drift evaluation and a reference comparison. Do not infer ankle torque, ground reaction force, nerve conduction velocity or neurological diagnosis from this recorder alone. It records surface muscle activity and segment inertial motion; it has no force, EEG or nerve-conduction measurement channel.

Record side, affected/unaffected status where approved, AFO model/setting, footwear, speed, task, order, rest, placement, electrode spacing, sensor orientation, normalization, filter choices and calibration. Use pseudonymous identifiers. Keep raw files immutable with SHA-256; derive CSV/features in separate folders. Store events with their source and uncertainty rather than aligning streams by row number.

## Evidence boundaries

The prior integrated simulations use behavioral peripherals and substituted storage/power. Their results remain useful for protocol, format and fault logic. This review does not convert them into measurements of ripple, electrode noise, patient safety, RF reliability or sustained hardware timing. The custom PCB needs a repeat of staged bring-up after the breadboard succeeds, particularly for switching loops, grounding, antenna and thermal behavior.

## Primary references

- [AD7606 original family datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf): supply, coding, timing, serial operation and reference.
- [MyoWare 2.0 advanced guide](https://cdn.sparkfun.com/assets/learn_tutorials/1/9/5/6/MyoWare_v2_AdvancedGuide-Updated.pdf): RAW/RECT/ENV and sensor use.
- [MIKROE 6DOF IMU 14 Click](https://www.mikroe.com/6dof-imu-14-click): selected carrier documentation.
- [SENIAM lower-leg placement](https://seniam.org/lowerleg_location.htm) and [fixation](https://seniam.org/fixation.htm): placement, orientation and consistent electrode geometry. The actual MyoWare geometry must be documented rather than assumed to match a recommendation.
