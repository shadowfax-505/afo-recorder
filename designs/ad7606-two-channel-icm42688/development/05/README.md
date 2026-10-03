# 05 - Second analog input and interaction

**Prerequisite:** Stage 4 accepted. **Firmware:** diagnostic-adc. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

Build BB2 and repeat every BB1 test. Swap test sources to prove identities. Drive one channel while the other is held at midpoint, then reverse. Measure idle, controller-active and later Wi-Fi-active noise separately.

## Acceptance checks

- **5-identity:** Repeat BB1 tests on BB2; exactly EMG1/2; common frame timestamp; no extra exported muscle channels
- **5-crosstalk:** Provisional <−40 dB crosstalk screen; generator feedthrough measured separately; preserve RMS noise and 10 min error log

## Send for review

- Both response tables
- 10-minute diagnostic error log
- baseline RMS/PSD with bandwidth
- driven and quiet channel amplitudes
- cable-layout photos

Provisional crosstalk screen is below -40 dB relative to the driven channel. A noise floor can only establish an upper bound: report that bound rather than claiming an exact crosstalk value. Research noise targets depend on the smallest effect to detect.

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
