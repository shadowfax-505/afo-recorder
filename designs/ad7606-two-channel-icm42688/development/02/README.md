# 02 - Controller and controls

**Prerequisite:** Stage 1 accepted. **Firmware:** diagnostic-controller. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

Add controller, button, LEDs and USB sense. Connect only according to the existing exact contact table. Check 20 boots/programming cycles, then USB sense attached/absent. Do not connect both external regulation and an unqualified DevKit USB power feed.

## Acceptance checks

- **2-controller:** 20 programming/reset cycles without failure; buttons and LEDs match controls
- **2-usb:** GPIO21 LOW attached / HIGH absent; attachment indicator 1/0; no USB VBUS feed into regulated 5 V; DevKit USB sockets empty

## Send for review

- Complete serial log
- binary SHA-256
- photos
- 20-cycle table
- GPIO21 voltage both states
- rail measurements under controller load

The diagnostic intentionally allows instrumented USB operation. It does not itself prove the recording interlock; repeat the actual recording inhibition test at stage 7.

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
