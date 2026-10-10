# 04 - First analog input

**Prerequisite:** Stage 3 accepted. **Firmware:** diagnostic-adc. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

Build only BB1 using MCP6002 and the exact placement/contact drawing. Keep ADC V2 at a known DC level. Check local decoupling, midpoint, then 1.5 V-biased 100 mVpp at 20, 100, 500 and 1000 Hz through the ADC; check 4000 Hz on the scope only (it is the 8 kHz Nyquist frequency). Keep generator output within 0.1-2.9 V including turn-on transients.

## Acceptance checks

- **4-response:** 1.5 V + 100 mVpp synthetic input at 20/100/500/1000 Hz via ADC (4 kHz on scope only); unity DC; measured response within simulated tolerance envelope plus ±0.5 dB margin; no person attached
- **4-bias:** Unplugged RAW settles 1.50 V ±30 mV; use safe 0.1–2.9 V sources for connected 3 V analog stage

## Send for review

- RAW1 and V1 simultaneous scope traces
- amplitude/phase at each frequency
- DC offset
- unplugged settling
- generator output settings and termination
- serial mean/RMS

Measure the voltage at the breadboard, not just the generator display: a 50-ohm setting into a high-impedance load can change delivered amplitude. Do not attach electrodes.

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
