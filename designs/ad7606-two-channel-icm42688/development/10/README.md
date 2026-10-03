# 10 - MyoWare integration and research readiness

**Prerequisite:** Stage 9 accepted; research protocol review separate. **Firmware:** breadboard-record-2ch. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

10A: verify VIN/GND/RAW routing and sensor integration with no person attached. 10B: approved supervised mounting protocol with all USB, chargers and instruments removed before electrodes attach. 10C: repeated placement, synchronized reference and labeled pilot tasks.

## Acceptance checks

- **10-sensor:** Correct VIN/GND/RAW pads and supply; no saturation or cabling fault; distinguish RAW volts from electrode-referred EMG
- **10-wearable:** Consent and safety review complete; mounting strain relief/AFO clearance checked; no lab instruments mains USB or charging while electrodes are attached

## Send for review

- Pseudonymous trial manifest
- placement/axis diagrams
- calibration files
- AFO/footwear/condition labels
- event/reference timestamps
- original recordings and quality
- protocol approval reference, not identifiable consent documents

Engineering stage completion does not authorize participants. Match sensor electrode spacing to the study and document deviations from SENIAM. AFO pressure, cable traction and movement artifact can alter EMG. Keep participant identity outside the project repository.

## Continuous regression

Before power: inspect the changed wiring against the contact table and photograph it. After power: remeasure every connected rail at the load, verify no unexpected heat/current, and rerun the last accepted diagnostic. Repeat earlier affected tests whenever a supply, cable, firmware or grounding connection changes. Record failures and repairs; retain the previous accepted evidence.

## If the gate fails

Stop acquisition and remove power before changing wiring. Disconnect only the last-added module and restore the last accepted configuration. Repeat its test. If it now fails, check the shared supply/ground and changed connections before replacing components. Never change multiple modules at once to chase a fault.

## Results

Fill measurements.csv; retain raw instrument files alongside screenshots. Outcome starts NOT TESTED. Include units, uncertainty, instrument model/settings, source voltage/load, firmware hash and filenames. Mark unmet criteria FAIL; missing evidence PENDING. Submit the whole stage folder, including failures. A completeness check is not engineering approval.

## Stage files

- [New wires](new-wires.csv): exact endpoints copied from the existing wiring table; keep earlier accepted wires. Power-isolation and qualification instructions above override connection order within a stage.
- [Probe contacts](probe-contacts.csv): available exact probe locations. An empty table means use the instrument instructions above.
- [Fixture parts](fixture-parts.csv): staged discrete fixture components from the existing BOM; this is not a complete procurement list for modules, tools or consumables.
- [Measurements](measurements.csv) and [submission metadata](submission.json).
