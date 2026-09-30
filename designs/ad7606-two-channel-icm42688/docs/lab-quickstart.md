# Build one working stage at a time

**This guide is only for AD7606 + two MyoWare RAW inputs + two ICM-42688-P carriers.** Use the [exact hole/contact tables](build-guide.html) beside the [interactive build view](../viewer/build.html). Power off before each addition. Record the result before continuing; an empty results cell means untested.

The numerical limits below are integration gates, not a calibration certificate or guaranteed performance. The filter envelope comes from `simulations/results/response.csv`; power, noise and timing still require measurements. Read the [virtual verification results and limits](virtual-verification.md), then complete the physical gates below before ordering the compact PCB.

| Step | Add only this | Instrument / check | Continue when | If it fails |
|---|---|---|---|---|
| 1 | Selected regulators and midpoint breadboard | DMM at rails; scope with short ground spring; current-limited supply and dummy loads | Digital rail 3.20–3.45 V; analog rail 2.94–3.06 V; ADC rail 4.75–5.25 V; midpoint 0.49–0.51 × measured analog rail. Check 5 V at 30 mA load as well as idle | Disconnect loads; confirm regulator type, polarity, grounds and local capacitors. Do not increase current limit to hide a short |
| 2 | ESP32, controls and USB detection | Flash `diagnostic-controller`; view USB serial; DMM on GPIO21 | Repeat 10 resets; button and LEDs match output; USB attached reports 1, removed reports 0; 3.3 V rail stays in range | Check common ground, pull-ups and Q2 orientation; use external sense-only USB wiring, not an unintended DevKit power path |
| 3a | AD7606 module, **without ESP32 signal leads** | Unpowered continuity plus DMM/scope on VIO, AVCC, reference and mode strap | Serial mode confirmed to the chip, VIO 3.20–3.45 V, AVCC 4.75–5.25 V; reference matches its selected mode; BUSY/DOUT never exceed the ESP32 input limit | Follow [module qualification](module-qualification.md); stop if strap identity or supply routing differs |
| 3b | ADC signal wires, inputs at known DC | `diagnostic-adc`; scope CONVST/BUSY/CS/SCLK; voltages 1 V on V1 and 2 V on V2 | 125 µs nominal trigger period; scope and log jitter, nominal 1 µs high pulse (at least 25 ns), BUSY normally within the 4.2 µs datasheet limit; 128 serial clocks; codes approximately 6554 / 13107, swapped voltages swap channels; error within ±64 codes with a suitable calibrated source/meter; no FAIL output | Wrong order/scale: check range, DOUTA, mode and grounds. Missing edges: check CVA/CVB/BUSY. Late-read error: inspect scope and firmware load |
| 4 | First complete analog path | Generator 1.5 V bias + 100 mVpp sine; probe RAW and ADC input | 20, 100 and 500 Hz gains within simulated tolerance envelope plus instrument uncertainty; 500 Hz nominal about −1.85 dB. Unplugged input settles near midpoint. Never drive below 0 or above 3 V in this test | Check both 3.3 kΩ and 47 nF stages, buffer orientation, supply and ground. Do not mistake bias voltage for muscle activity |
| 5 | Second analog path | Repeat step 4; drive one input while holding the other at midpoint | Both identities correct; no swapped inputs or clipping in intended signal range. Save noise and crosstalk measurements; set study-specific limits before claiming research suitability | Separate cables, inspect common impedance and analog supply; repeat with Wi-Fi disabled |
| 6 | Foot carrier, then shank carrier | `diagnostic-imu-one`, then `diagnostic-imu-two`; scope both INT1 lines | WHO_AM_I/readback pass; both FIFO counts and interrupt counts advance about 200/s; at rest one axis near ±1 g, remaining axes near 0 g; no overflow or missing-interrupt failure | Verify SPI jumpers, CS identities, INT1, 3.3 V and orientation. First-interrupt grace is 100 ms; it is not permission for a missing wire |
| 7 | SD adapter/card | `breadboard-sd-only-2ch`; record synthetic inputs, convert file | A 60-minute run has no unexplained counter gaps; metadata names two inputs; full-card and power-cut tests report errors or recover only verified records | Check GPIO47 CMD, GPIO39 CLK, GPIO40 D0, all five adapter contacts, pull-ups and card supply |
| 8 | Wi-Fi enabled | `breadboard-record-2ch`; run laptop viewer while SD continues | Only EMG1/2 shown; lost Wi-Fi packets visible; SD conversion still passes counter/CRC checks | Wireless gaps are not SD gaps; compare both logs. Reduce preview load only after identifying the bottleneck |
| 9 | Protected battery | Repeat full load, unplug all mains/USB; log supply and runtime | At least two hours measured runtime; 10 repeatable starts/stops; safe pack cutoff and no hot components | Record actual current, temperature and low-battery events; simulator power estimates cannot replace this |
| 10 | Bare MyoWare sensors and mounting | First test sensors electrically with no person attached; then follow institutional supervised protocol | Clearance, retention, cable strain and artifacts checked; required consent/safety review complete | Return to the last passing stage. Never attach a person while using lab instruments, charging, USB or mains-connected cables |

For steps 3–6, diagnostic acquisition runs in approximately one-second windows and stops ADC triggering before printing. **The spaces between diagnostic windows are intentional.** Use the recording builds for continuous capture and endurance tests.

Use `record-2ch` only on the custom PCB (SD CMD GPIO38). It is not interchangeable with the breadboard image. Flash all three files at the addresses in the chosen manifest.

## Results sheet

Copy one row per test; include failures and retests. Do not prefill these with simulator output.

| Date / operator | Stage / firmware SHA-256 | Module serial or photo | Instrument / calibration | Applied stimulus / load | Measured value | Limit / uncertainty | Pass/fail / notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

After all laboratory stages, the final PCB still needs power startup, switching ripple, antenna/USB, thermal, noise, crosstalk and sustained recording checks. Breadboards validate the logical signal path, not the final board layout.

At ADC initialization the firmware clocks a discarded read during RESET to establish SPI mode. No acquisition trigger or counted sample occurs during that read. Identify it separately on the scope; the first counted conversion must have the expected DC codes. A diagnostic failure latches and requires reset/restart after correcting the cause.
