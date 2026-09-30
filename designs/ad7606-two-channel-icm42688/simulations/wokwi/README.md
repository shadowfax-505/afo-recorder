# ESP32-S3 protocol simulation

This project uses the **actual stage-6 ESP-IDF diagnostic firmware**, not an Arduino replacement. The seven recorded cases are historical evidence for the preserved tested image; current recompiled diagnostic images have not been rerun. `firmware/merged.bin` combines the bootloader, partition table and application; `firmware/afo_recorder.elf` is the corresponding ELF. The two EMG codes are 6554 and 13107 (approximately 1 V and 2 V at ±5 V full scale). Both IMU instances use the same source and separate state, FIFOs and timers.

**Historical status: seven actual ESP32-S3 diagnostic scenarios passed in Wokwi CLI on the preserved source/image snapshot.** See [tested image/source hashes](tested-diagnostic-20260930/manifest.json), the [historical verification report](../../docs/virtual-verification.md), [scenario results](results/scenarios.json), serial logs, compressed VCDs and protocol summaries in `results/`. Startup SPI initialization and a shared diagnostic fault latch correct two issues exposed by execution. Historical failed attempts remain labeled as historical. Preserved v1.5 recorder/FatFS/lwIP integration is reported separately in the [integrated report](../../docs/integrated-verification.html): ten complete CLI/firmware passes, an additional nominal firmware/file/UDP pass, one partial battery capture and four quota refusals. Current v1.6 additionally checks BUSY assertion after CONVST and awaits its whole-system rerun because quota is exhausted. The full matrix remains incomplete; physical testing is outstanding.

## Run

1. Install [Wokwi CLI](https://github.com/wokwi/wokwi-cli). Configure `WOKWI_CLI_TOKEN` locally using the [Wokwi CI dashboard](https://wokwi.com/dashboard/ci). Never put the token in the repository.
2. From this directory run `wokwi-cli chip compile chips/ad7606.chip.c -o chips/ad7606.chip.wasm` and the corresponding command for `icm42688.chip.c`.
3. Choose the image first. `firmware/` contains the current recompiled diagnostic image; reproducing the historical seven cases requires the image under `tested-diagnostic-20260930/simulations/wokwi/firmware/`. Keep historical results unchanged and record every new run in a fresh directory. Run `python3 run_scenarios.py`. It creates serial logs, VCD traces and expected-versus-observed results in a fresh `results/run-*` directory for each invocation. Missing output is a failure. A nonzero exit or failed scenario must never be treated as a pass.
4. For manual browser use, create an ESP32-S3 project; upload both `.chip.c`/`.chip.json` pairs, replace `diagram.json`, then use F1 → **Upload Firmware and Start Simulation** with `firmware/merged.bin`. USB serial/JTAG must be selected in the diagram. Do not press the Arduino build button and mistake that output for the diagnostic binary.

## Limits

- AD7606 behavioral conversion is 4 µs; fault modes are stuck BUSY, 250 µs BUSY and disabled serial output. The wrong-mode test is rejected by comparing known DC codes, not by a nonexistent ADC identity register.
- ICM model implements only the register subset this driver uses, 16-byte FIFO records, wraparound timestamps, identity/readback, overflow, absent sensor and missing interrupts. It does not independently certify all reserved bits, sensor filtering or chip startup physics.
- The diagrams represent digital protocol nets. Analog supplies, protection, reference, noise and MyoWare behavior are outside Wokwi's model. Use ngspice results alongside this, never as proof of the received module's straps.
- `cpuFrequency=max` prevents the usual 8 MHz emulator cap from making an 8 kHz diagnostic fail solely because of that cap; simulation can be slow. Neither wall-clock speed nor successful virtual timing measures real ESP32 jitter.
- SD is deliberately absent: existing firmware uses SDMMC, whereas Wokwi's microSD model uses SPI. The separate integrated recorder harness exercises production FatFS/lwIP with a substitute block medium and UDP loopback; the supplied SPI microSD model still cannot validate this recorder’s SDMMC interface. No battery runtime or radio measurements are implied.

## Native model tests

Compile `tests/chips_test.c` with a C compiler, once with `-DADC_MODEL` and once without. `-Wno-unknown-attributes` silences Wokwi WASM annotations when using native Clang. These tests use mock Wokwi callbacks and exercise the actual model sources; they do not run ESP-IDF.

The API header was downloaded from [Wokwi's official Chips API](https://wokwi.com/api/chips/wokwi-api.h). Keep its provenance distinct from project code.

## Evidence safeguards

The runner rejects stale files, partial windows, missing conversions, incorrect channel extrema, incorrect IMU identity or rate, empty/header-only VCD files, nonzero process exits and timeouts. Nominal gates are 8 kHz ±1% over a roughly one-second window and 195–205 IMU samples/interrupts per window. The serial-disabled case requires the model's exact all-ones signature; arbitrary incorrect data is not sufficient.

`verify_trace.py` checks 128-clock frame lengths, all eight signed words, modeled BUSY timing, conversion periods and specific fault signatures. The analyzer has a one-million-event buffer, so the normal VCD ends before the 2.5-second serial run. A partial last SPI frame is reported and excluded; complete captured frames are checked. Capture coverage is stated in each result. Do not extend this into a claim of long-term or physical timing validation.

Run `python3 -m unittest discover -s tests -p 'test_*.py' -v` here to reproduce the 15 runner regression tests. These use synthetic logs and traces to test the evidence gate; they are separate from the 40 converter/host tests and do not validate physical electronics or simulator execution.
