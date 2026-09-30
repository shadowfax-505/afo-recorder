# ESP32-S3 protocol simulation

This project uses the **actual stage-6 ESP-IDF diagnostic firmware**, not an Arduino replacement. `firmware/merged.bin` combines the bootloader, partition table and application; `firmware/afo_recorder.elf` is the corresponding ELF. The two EMG codes are 6554 and 13107 (approximately 1 V and 2 V at ±5 V full scale). Both IMU instances use the same source and separate state, FIFOs and timers.

**Status: not yet a passing Wokwi system test.** A browser attempt stalled with SPI2 MISO contention warnings. The CLI attempt could not run without a locally configured token. These are unresolved simulation issues; they do not establish physical failure or success. See `results/browser-attempt.txt`. No successful virtual logic trace is supplied. Native custom-chip unit tests and WASM compilation are separate checks, not ESP32 execution.

## Run

1. Install [Wokwi CLI](https://github.com/wokwi/wokwi-cli). Configure `WOKWI_CLI_TOKEN` locally using the [Wokwi CI dashboard](https://wokwi.com/dashboard/ci). Never put the token in the repository.
2. From this directory run `wokwi-cli chip compile chips/ad7606.chip.c -o chips/ad7606.chip.wasm` and the corresponding command for `icm42688.chip.c`.
3. Run `python3 run_scenarios.py`. It creates serial logs, VCD traces and expected-versus-observed results in a fresh `results/run-*` directory for each invocation. Missing output is a failure. A full successful run is required before changing this status.
4. For manual browser use, create an ESP32-S3 project; upload both `.chip.c`/`.chip.json` pairs, replace `diagram.json`, then use F1 → **Upload Firmware and Start Simulation** with `firmware/merged.bin`. USB serial/JTAG must be selected in the diagram. Do not press the Arduino build button and mistake that output for the diagnostic binary.

## Limits

- AD7606 behavioral conversion is 4 µs; fault modes are stuck BUSY, 250 µs BUSY and disabled serial output. The wrong-mode test is rejected by comparing known DC codes, not by a nonexistent ADC identity register.
- ICM model implements only the register subset this driver uses, 16-byte FIFO records, wraparound timestamps, identity/readback, overflow, absent sensor and missing interrupts. It does not independently certify all reserved bits, sensor filtering or chip startup physics.
- The diagrams represent digital protocol nets. Analog supplies, protection, reference, noise and MyoWare behavior are outside Wokwi's model. Use ngspice results alongside this, never as proof of the received module's straps.
- `cpuFrequency=max` prevents the usual 8 MHz emulator cap from making an 8 kHz diagnostic fail solely because of that cap; simulation can be slow. Neither wall-clock speed nor successful virtual timing measures real ESP32 jitter.
- SD is deliberately absent: existing firmware uses SDMMC, whereas Wokwi's microSD model uses SPI. Storage and Wi-Fi fault checks remain software models. No battery runtime or radio measurements are implied.

## Native model tests

Compile `tests/chips_test.c` with a C compiler, once with `-DADC_MODEL` and once without. `-Wno-unknown-attributes` silences Wokwi WASM annotations when using native Clang. These tests use mock Wokwi callbacks and exercise the actual model sources; they do not run ESP-IDF.

The API header was downloaded from [Wokwi's official Chips API](https://wokwi.com/api/chips/wokwi-api.h). Keep its provenance distinct from project code.

## Evidence safeguards

The runner rejects stale files, partial windows, missing conversions, incorrect channel extrema, incorrect IMU identity or rate, empty/header-only VCD files, nonzero process exits and timeouts. Nominal gates are 8 kHz ±1% over a roughly one-second window and 195–205 IMU samples/interrupts per window. The serial-disabled case requires the model's exact all-ones signature; arbitrary incorrect data is not sufficient.

VCD validation currently proves **signal activity only**, not correct clock edges, 128-clock frame length or BUSY timing. Those still need protocol-level trace inspection after Wokwi completes a run. Simulator failure remains unresolved and no passing ESP32 system test is claimed.

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` here to reproduce the 14 runner regression tests. These use synthetic logs and traces to test the evidence gate; they are separate from the 40 converter/host tests and do not validate physical electronics or simulator execution.
