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
