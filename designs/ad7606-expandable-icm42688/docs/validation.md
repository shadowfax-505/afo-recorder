> Historical baseline report. Current results and terminal status: [validation-report.md](validation-report.md). Statements below describe the earlier baseline, not current mapping completeness.

# Validation and release status

Engineering prototype; **NOT cleared for fabrication or human use**. No boards ordered. No hardware flashed, measured, worn or safety-certified during this work.

## Completed software and simulation evidence

- Host unit tests cover legacy files, metadata, enabled channels, signed ADC bounds, malformed records, integrity checks and Wi-Fi handling. See host-tests.txt for the final run.
- Acquisition model:14 scenarios (2/4 channels × normal, delayed SD writes, overflow, missing EMG, missing IMU, BUSY timeout, interrupted power). Model records pass through the real converter; injected losses produce report issues. Simulations are2 s examples, not a60 min ESP32 test.
- ngspice external analog model: 16 R±1%/C±10% corners; maximum nominal analytical deviation 0.002625 dB below20 kHz. Synthetic sources approximate MyoWare RAW output; buffers are labeled substitute1 MHz models. Ideal ADC quantization/clipping is separate. No physical noise, crosstalk or effective-resolution result is claimed.
- Firmware cross-compilation profiles and image hashes are in firmware/builds. Each manifest identifies ADC, enabled channels, diagnostic stage and flash offsets. Rebuild with hardware=breadboard for lab metadata; supplied images identify pcb.
- Final ERC, DRC and pin/parity reports reside beside this document. Review their actual counts and ignored checks, not only PASS labels. Consistency covers schematic XML, actual PCB pad export, firmware GPIO assignments, viewer pad endpoints and breadboard component values/hole occupancy. It does not validate unknown module headers or all analog behavior.
- Browser checks exercise breadboard/PCB views, stage selection,2/4 channel selection, assembly separation and component details for both packages. Module geometry remains approximate. Live software test uses a loopback synthetic AD7606 stream, not ESP32 radio transmission.

## What blocks ordering

1. Verify actual ADC module header positions, VIO, serial selection, data output, reference/clock/input loading. Select and verify exact ready-made IMU and controller modules. ADS lab availability remains a dependency.
2. Complete independent electrical and assembly review, including every IC pin/land pattern, regulator loops/current capacity, decoupling/reference routing, USB impedance/return paths, connector mating orientation and antenna clearance. A DRC pass cannot replace this review. The AD7606 charge-pump placement was revised after the first DRC pass for this reason.
3. Perform and sign the staged lab tests. Confirm numerical screening targets are suitable for the planned research; do not substitute simulation for measured noise/crosstalk/timing.
4. Final review must accept the exact manufacturing export hashes after the final routing pass. Do not use older copied exports.

## Physical tests still required

All stages in stage-results.csv are NOT TESTED. Required evidence includes rail startup/ripple/load response/temperature, reverse-polarity and USB-backfeed behavior, USB recording inhibition, ADC logic levels/DC calibration/trigger timing/channel simultaneity, frequency response/noise/clipping/crosstalk, IMU rates/orientation/cable limits,60 min sustained SD tests and recovery/full-card behavior, simultaneous Wi-Fi stress,≥2 h measured battery runtime, mounting and supervised institutional safety/ethics review.

The breadboard uses functionally corresponding analog networks, DIP amplifier packages and modules. Its test-only substitutions are explicit in module-verification.md. It cannot validate final-board power distribution, RF coexistence, layout-dependent analog interference or patient fit. Retest those properties on the compact PCB.

## Reproducing checks

Install host/requirements.txt. Use Python3 for host tests and simulations. ngspice_runner.py finds a local shared library or accepts NGSPICE_LIBRARY. KiCad10 exports/DRC use kicad-cli; the PCB-pad exporter requires KiCad's pcbnew Python. Do not regenerate or reroute the delivered PCB just to inspect it.

```sh
python3 -m unittest discover -s host/tests
python3 simulations/run_analog.py
python3 simulations/run_acquisition.py
python3 design/validate_package.py
```

Set PYTHONPATH=host for the unit-test invocation. `validate_package.py` consumes existing exported netlists/pad geometry; regenerate these with the provided KiCad exporters after editing a design. Manufacturing outputs are not auto-ordered.

## Detailed assembly viewer update — 2026-09-27

The default viewer now provides a focused analog breadboard insertion guide with numbered holes, DIP pin mapping, one-jumper steps, strip inspection and printable tables. The earlier system/PCB view is retained at `viewer/assembly.html`. Connectivity checks are in `breadboard/assembly-checks.json`; browser interaction checks are in `precision-viewer-check.txt`. This update does not change the PCB, firmware or prior physical-test status. External module and carrier pin maps are still unreleased; stages requiring those connections remain incomplete.
