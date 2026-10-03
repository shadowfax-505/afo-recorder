# 03 - ADC module and two DC inputs

**Prerequisite:** Stage 2 accepted. **Firmware:** diagnostic-adc. **Status: NOT TESTED.**

[Sequence overview](../README.md) | [Exact contacts](../../docs/build-guide.html) | [3D assembly](../../viewer/build.html)

## Add and test

3A: qualify module power/straps with ESP32 signal leads disconnected. 3B: add shared CVA/CVB trigger, BUSY, reset and SPI. Keep unused analog inputs at their documented levels. Apply measured 1 V/2 V DC and swap them. Do not connect analog buffers yet.

## Acceptance checks

- **3-module:** AVCC 4.75–5.25 V; VIO 3.23–3.43 V (project target); internal reference and serial strap verified; ESP32-safe output levels; RANGE/OS low
- **3-common-trigger:** GPIO11 through DIST1 a29/b29/c29 reaches both CVA/CVB; common rising edge
- **3-dc:** 1 V / 2 V ideal 6554 / 13107; compute from measured source; ±65 codes plus measured uncertainty; swapping sources swaps EMG identities
- **3-prime:** Normally one discarded read per diagnostic boot; no measurement CONVST or saved sample; first measured DC codes correct
- **3-serial:** 128 clocks; 8 MHz; mode 2 idle HIGH / falling-edge sample; eight signed words V1–V8, only V1/V2 exported
- **3-busy:** CONVST high ≥25 ns; conversion 3.45–4.2 µs with oversampling off; SCLK after BUSY fall; 80 µs is fault deadline only
- **3-rate:** 125 µs intervals ±1%; 8 kHz ±0.1% over 60 s of acquisition; exclude diagnostic print pauses; no unexplained timeout/overrun

## Send for review

- Module continuity table and strap close-ups
- VIO/AVCC/reference voltages
- raw logic trace with RESET, CONVST, BUSY, CS, SCLK and DOUTA
- serial windows
- both measured DC voltages before/after swap

AD7606 has no register identity or frame CRC. Prove identity, range and channel order using known voltages. DB7 is DOUTA in serial mode; do not infer header orientation from the chip pin numbers.

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
