# 07 - Original SD recording

**Prerequisite:** Stage 6 accepted. **Firmware:** breadboard-sd-only-2ch. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

7A: short known-signal recording and conversion. 7B: 60-minute continuous run. 7C: absent/full-card and five interrupted-write trials on expendable media. Test recording USB inhibition with synthetic signals only. Stop and wait for recording LED off before removing media.

## Acceptance checks

- **7-format:** AD7606 / two inputs / ICM / breadboard metadata; RAW code ×5/32768 V; scale 1 midpoint offset 0; retain raw IMU counters IRQ anchors read start/end and timing flags
- **7-endurance:** CMD GPIO47 CLK GPIO39 D0 GPIO40; container CRC32 and counters pass; no unexplained saved gaps/queue errors; END and expected stop reason; no sync/close failure
- **7-usb:** Refuse start with USB attached; attach during synthetic recording gives explicit stop/error; no person attached
- **7-storage-faults:** No-card refuses start; full-card explicit stop; five controlled interruptions preserve only CRC-valid records and report truncated tail/missing END
- **7-timestamps:** Normal 65.536 ms counter wraps handled; host estimate flag 2 retained; startup count differences not row-aligned; no unexplained gap/invalid/timing rejection

## Send for review

- Unmodified .afolog files
- converter command/version
- metadata, quality report and CSV excerpts
- stop reason
- serial log
- card make/capacity/filesystem
- scope trace of continuous conversion cadence

Keep damaged originals; do not overwrite them with recovered files. END is not proof of successful final filesystem sync. Check close/sync faults and counters independently. Diagnostic printing pauses cannot be used as continuous-acquisition evidence.

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
