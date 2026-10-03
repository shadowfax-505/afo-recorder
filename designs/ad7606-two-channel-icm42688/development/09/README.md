# 09 - Battery and full-load regression

**Prerequisite:** Stage 8 accepted. **Firmware:** breadboard-record-2ch. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

Remove both lab supply leads. Check protected pack polarity before connection. Log actual runtime for at least two hours, voltage/current/temperature and low-battery events; repeat 20 starts/stops. Firmware session limit is two hours: document restart if runtime testing continues.

## Acceptance checks

- **9-battery:** Both lab-supply leads removed; ≥2 h measured runtime; 20 repeatable startups/shutdowns; complete 60 min trial; record pack voltage age temperature and events

## Send for review

- Timestamped battery log
- pack rating/age/protection details
- start/stop table
- resulting original files
- peak-current and voltage-dip captures using the approved no-person bench arrangement

Battery protection does not provide patient isolation. Battery warning/stop thresholds are firmware decisions, not proof that the pack protection trips correctly. Do not bypass protection or intentionally overdischarge.

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
