# Define the research claim before collecting the study

Complete with the supervisor and, where applicable, clinical collaborators. This is not a prescribed clinical protocol.

| Decision | Write before collection | Why it matters |
|---|---|---|
| Primary question | One testable AFO or neuromuscular hypothesis | Avoid choosing an attractive result after analysis. |
| Primary outcome | Exact feature, units, time window and normalization | “Muscle activity” is not a complete outcome definition. |
| Meaningful difference | Smallest effect worth detecting | Determines required noise, repeatability and timing performance. |
| Reference | Independent gait-event, angle or task reference and its uncertainty | IMU-estimated events cannot validate themselves. |
| Participants and unit | Participant/session/trial structure; eligibility under protocol | Thousands of samples from one person are not thousands of independent participants. |
| Conditions | AFO configuration, footwear, walking speed, order and rest | These can change signals independently of the intervention. |
| Placement | Anatomical landmarks, spacing, side, mounting axes, repeatability | Sensor changes can masquerade as physiology. |
| Calibration | Electrical calibration, IMU bias/alignment, EMG normalization | Physical units alone do not establish comparability. |
| Timing budget | Allowed alignment uncertainty for the intended outcome | 200 Hz motion does not provide arbitrarily precise event timing. |
| Quality rules | Saturation, dropout, artifact and missing-label exclusion rules | Make decisions before examining condition effects. |
| Analysis | Filtering, windowing, model, repeated-measures treatment | Preserve participant independence and avoid data leakage. |
| Data protection | Pseudonyms, access, retention and institutional approval | Research recordings and clinical information may be sensitive. |

Examples to discuss, not approved studies:

- **AFO comparison:** normalized TA activation during independently labeled swing, with controlled speed and within-participant conditions. Requires validated event labels and reliable normalization.
- **Neuromuscular coordination:** TA/medial-gastrocnemius coactivation under defined tasks. Requires an explicit coactivation formula and consideration of electrode placement and physiological crosstalk.
- **Movement monitoring:** foot/shank motion features during a prescribed task. Requires mounting calibration and appropriate reference validation; do not call inferred ankle angle a direct measurement.

For machine learning, split by participant when claiming generalization to new people. Keep overlapping windows from the same trial together; otherwise train/test leakage can inflate results. Determine sample size from the chosen outcome and study design, not the 8 kHz sample count. A pilot estimates feasibility and variance; it does not establish diagnostic accuracy.

## What this recorder fixes before you choose an outcome

| Signal | Fixed by the build | Research consequence |
|---|---|---|
| EMG sampling | 8,000 simultaneous frames/s; one code = 152.588 µV at the ADC input (±5 V range) | Ample for surface-EMG bandwidth; values are MyoWare RAW-output volts, not electrode-referred microvolts |
| EMG analog path | Two buffered 3.3 kΩ/47 nF poles (each about 1,026 Hz; combined −3 dB about 660 Hz, −1.85 dB at 500 Hz) plus the MyoWare's own RAW filtering | Report both filters; frequency features (for example median frequency) depend on them |
| IMU sampling | 200 Hz per sensor, ±16 g and ±2000 °/s (2,048 counts per g; 16.384 counts per °/s) | Samples are 5 ms apart; event timing from motion alone has millisecond-scale uncertainty |
| IMU filtering | On-chip UI filter, second order, bandwidth index 4 (`GYRO_ACCEL_CONFIG0 = 0x44`). TDK's driver names this the "/10" setting; the datasheet scales it from max(400 Hz, ODR), giving roughly 40 Hz at 200 Hz | Suitable for segment kinematics; it attenuates sharp heel-strike impact transients. If impacts are an outcome, the ODR and filter must change and be revalidated |
| IMU time | Sensor clocks are independent; FIFO ticks last 32/30 µs (firmware 1.8); host times are estimates anchored to interrupts | Measure offset and drift against a reference before claiming EMG–motion timing |

## Bench timing-alignment check (before participants)

1. Choose one physical event that a reference system and the recorder both see, for example a sharp tap on the foot carrier recorded by a reference accelerometer or motion-capture marker. For EMG timing, inject a generator pulse into the synthetic-input fixture while the reference system logs the generator's sync output. Bench only; no person attached.
2. Repeat the event at least 20 times across a 10-minute recording.
3. For each event, record the reference time and the recorder time (EMG `conversion_trigger_host_us`, IMU `host_time_estimate_us`). Fit offset and drift; report the residual spread as the alignment uncertainty.
4. Enter the results in the session manifest's `synchronization` fields (`offset_us`, `uncertainty_us`, `drift_test_file`) and compare them with the timing budget written above.

## Sample size: an illustration, not a calculation for your study

For a within-participant comparison (two AFO conditions, paired t-test, two-sided α = 0.05, power 0.80), the required number of participants depends on the standardized effect dz = mean paired difference ÷ standard deviation of the differences:

| dz | Participants |
|---|---|
| 0.5 | 34 |
| 0.8 | 15 |
| 1.0 | 10 |
| 1.2 | 8 |

Estimate the standard deviation of the differences from a pilot or prior literature, using your chosen outcome, normalization and placement procedure. Add allowance for dropouts and excluded trials, and use a design-appropriate method (for example mixed models with repeated trials) for the final analysis. Trial or sample counts do not substitute for participants.
