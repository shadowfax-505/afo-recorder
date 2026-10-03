# 08 - Wi-Fi while SD records

**Prerequisite:** Stage 7 accepted. **Firmware:** breadboard-record-2ch. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

First repeat a short baseline without a receiver, then a 60-minute SD+Wi-Fi trial. Interrupt and reconnect laptop reception. Compare common record identities, codes and timestamps; never fill missing preview data silently.

## Acceptance checks

- **8-live:** 60 min; only EMG1/2; explicit preview losses; independently audit original SD counters/CRC/END/stop and confirm no unexplained saved loss
- **8-disconnect:** Disconnect/reconnect produces visible preview gaps; compare identities codes timestamps and stop/error indications without filling missing data

## Send for review

- Original SD file AND laptop raw archive
- receiver log/quality
- disconnect times
- laptop OS/software version
- both converted outputs
- new rail/noise captures under wireless load

A smooth dashboard is not an acceptance test. Wireless loss must be visible, while independently checking that SD did not lose records.

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
