# 01 - Qualify power one rail at a time

**Prerequisite:** Stage 0 reviewed. **Firmware:** None. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

1A: digital regulator alone. 1B: 5 V regulator alone. 1C: 3 V analog regulator fed from the accepted digital rail. 1D: midpoint buffer. Test idle first, then dummy loads. Keep ESP32, ADC, IMUs and MyoWare disconnected. Use the selected regulator modules; do not breadboard switching IC loops.

## Acceptance checks

- **1-polarity:** No rail short; correct source polarity; lab supply only, battery disconnected
- **1-digital:** 3.23–3.43 V at 0/100/300 mA; ripple ≤50 mVpp (20 MHz bandwidth); provisional project screen
- **1-analog:** 2.94–3.06 V at 0/20/50 mA; midpoint 0.49–0.51 × measured analog rail; ripple ≤10 mVpp; provisional project screen
- **1-adc-supply:** 4.8–5.2 V at 10–50 mA; never exceed 5.25 V during startup

## Send for review

- Rail DMM readings
- startup and load-step scope traces
- supply current/limit
- dummy-load resistance and rating
- temperature versus time

Measure polarity before enabling. Begin with unloaded module current limit appropriate to its documented startup requirement; log the chosen setting. If limiting occurs, disable and diagnose rather than repeatedly increasing it. No universal safe current limit is assumed.

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

## Dummy-load examples

Use R = V / I and P = V x I. Approximate examples: 3.3 V at 300 mA needs 11 ohms and dissipates 0.99 W (use at least a 2 W resistor); 5 V at 50 mA needs 100 ohms and dissipates 0.25 W (at least 0.5 W); 3 V at 50 mA needs 60 ohms and dissipates 0.15 W (at least 0.5 W). Measure actual resistance/current, keep hot loads away from plastic, and remain within regulator ratings. Switch between load points with power off unless using a qualified electronic load. Current limit and startup capture are recorded evidence, not fixed universal settings.
