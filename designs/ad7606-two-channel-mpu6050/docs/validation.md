> Historical baseline report. Current results and terminal status: [validation-report.md](validation-report.md). Statements below describe the earlier baseline, not current mapping completeness.

> MPU variant: [mpu6050-wiring-and-timing.md](mpu6050-wiring-and-timing.md) is authoritative for sensor wiring, timing and current release gates. Inherited ADC/analog instructions remain applicable.

# Fixed-two AD7606 validation — 2026-09-26

Engineering prototype, pending lab tests and independent design review. No hardware was flashed, measured, worn or ordered.

## Completed checks

- KiCad 10.0.6 ERC: zero violations. DRC: zero violations and zero unconnected items under the saved project rules. Consult `erc.json` and `drc.json`, including their ignored checks. Courtyard/filter/type checks are not all enabled; this is not assembly sign-off.
- Schematic-to-specification, PCB pads, firmware GPIO and viewer consistency: PASS, 390 functional pins. No signal tracks on the reserved In1.Cu ground layer. Removed EMG3/EMG4 components and V3–V8 grounding are checked. Actual module headers remain unverified.
- Exactly two physical EMG connectors; 18 input-circuit components removed. Unused U3/U4 amplifier halves are terminated. The 75 × 50 mm four-layer outline is retained. Re-exported Gerbers, drills, placement, BOM, assembly drawing, schematic, STEP and GLB follow the final PCB.
- Seven ESP-IDF 5.4.2 profiles cross-compiled: PCB recorder, breadboard recorder, breadboard SD-only, controller diagnostic, ADC diagnostic, one-IMU diagnostic and two-IMU diagnostic. Each manifest records two active channels, hardware identity, Wi-Fi setting, offsets and image hashes. No four-channel image is supplied.
- 39 host tests passed, including fixed-two circuitry, disabled slots, ADC limits, legacy formats and an actual compile rejection for four-channel firmware. C-generated AD7606 records decode through the Python reader with valid CRC.
- A live receiver omission discovered during checking was fixed in this package: kind-7 AD7606 sample sequences now contribute to sample-gap reports. A regression test injects a missing EMG frame without any missing UDP packets and verifies the gap is reported. Existing packages were preserved.
- Seven synthetic acquisition scenarios: normal, delayed SD writes, queue overflow, missing EMG, missing IMU, BUSY timeout and interruption. Generated records passed through the converter; fault cases show issues. These short software scenarios are not a 60-minute ESP32 test.
- ngspice: both analog channels, 16 R±1%/C±10% corners, analytical comparison below 20 kHz. Maximum nominal difference approximately 0.002625 dB. Buffer model is an explicitly labeled 1 MHz substitute, not a manufacturer macromodel. Synthetic RAW signals and separate ideal ADC quantization/clipping do not measure noise, crosstalk or effective resolution.
- Browser: breadboard/PCB switching, stages, assembly separation, component/net details and the fixed-two selector checked. Screenshots are included. Model shows BB0 midpoint plus BB1/BB2 and two MyoWare blocks. External modules remain approximate with functional terminal positions.
- Loopback synthetic UDP stream: two EMG plots, synthetic warning and intentional dropped packets visible. Final receiver report includes AD7606 frame gaps. This does not test an ESP32 radio or electrical interference.

## Required before ordering and wearable use

Verify actual RBD-3184 header numbering, VIO, serial straps, DOUT and reference configuration. Select and verify controller and ready-made IMU modules. Complete independent schematic/footprint, regulator loop, decoupling, USB, antenna and assembly review. Complete and sign staged lab gates in `stage-results.csv`, all currently NOT TESTED.

Measure power startup/load/ripple/temperature, interlocks, ADC calibration/timing/noise/crosstalk, IMU orientation and rate, 60-minute SD recording/fault recovery, simultaneous Wi-Fi load and at least two hours of battery runtime. Repeat layout-dependent tests on the final PCB. Instrument-connected tests use synthetic signals with no person attached. Institutional and electrical-safety requirements precede supervised human recordings.

## Reproduce

From this package directory with required host dependencies and ngspice installed:

```sh
PYTHONPATH=host python3 -m unittest discover -s host/tests -v
python3 simulations/run_analog.py
python3 simulations/run_acquisition.py
python3 design/validate_package.py
```

Consistency consumes exported netlists/pad geometry; re-export after changes. KiCad exporters need KiCad 10 and pcbnew Python; tool paths may need adjustment on another computer. Firmware commands are in staged-build-guide.md. Manufacturing files are engineering-prototype outputs and are not automatically ordered.

## Detailed assembly viewer update — 2026-09-27

The default viewer now provides a focused analog breadboard insertion guide with numbered holes, DIP pin mapping, one-jumper steps, strip inspection and printable tables. The earlier system/PCB view is retained at `viewer/assembly.html`. Connectivity checks are in `breadboard/assembly-checks.json`; browser interaction checks are in `precision-viewer-check.txt`. This update does not change the PCB, firmware or prior physical-test status. External module and carrier pin maps are still unreleased; stages requiring those connections remain incomplete.
