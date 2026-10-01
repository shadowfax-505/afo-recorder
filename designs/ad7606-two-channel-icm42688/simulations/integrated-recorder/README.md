# Integrated recorder simulation

This project executes the production AD7606/two-input/ICM recorder using ESP-IDF v5.4.2 on Wokwi ESP32-S3. Acquisition, queues, FatFS writes, Wi-Fi startup and lwIP UDP run together. It is a simulation-only fixture; never flash its image onto the recorder.

The SDMMC mount is replaced with a sparse PSRAM block medium while FatFS/VFS remain real. Battery voltage, button and USB inputs are defined fixture values. Actual UDP datagrams go to a subscriber inside the emulated MCU; there is no laptop radio measurement. ADC/IMU devices are behavioral models. Four extra case-selector GPIOs belong only to the fixture and are absent from the recorder circuit.

Read [the integrated report](../../docs/integrated-verification.html) before interpreting the evidence. The [preserved v1.5 ledger](results/current/summary.json) contains ten completed CLI/firmware cases; nominal file/UDP checks also pass, with an optional VCD transport failure. The low-battery export is incomplete and four cases did not run because of the account quota. Its exact compiled sources, configuration, models and image are in [tested-source-1.5](tested-source-1.5/manifest.json).

The current image is **v1.6**, including BUSY-high confirmation and the startup stack-allocation correction. **All eighteen current cases pass through the supported Wokwi web editor**, with complete file/UDP exports and actual host checks. [Current ledger](results/web-current/summary.json) · [web reproduction files](web/README.md). Current byte/capture timing checks do not establish a downloaded VCD; no current waveform retrieval is claimed. The preserved CLI quota refusal and v1.5 partial outcomes remain unchanged. Twelve independent native model groups separately pass under sanitizers. Physical acceptance remains unperformed.

## Reproduce

Activate ESP-IDF v5.4.2 with the ESP32-S3 toolchain, then run:

```sh
python3 build_firmware.py --build-dir /path/to/external/integrated-build
python3 run.py --case normal --out /path/to/new-evidence-directory
python3 run.py --jobs 4 --out /path/to/new-full-matrix-directory
python3 -m unittest discover -s tests -v
```

Configure the Wokwi credential privately in `WOKWI_CLI_TOKEN`. Do not put it in source, a command argument, logs or version control. `WOKWI_CLI` can select the CLI executable. Every case requires a new directory. The runner validates image/source/model hashes, complete export terminators, contiguous byte offsets, binary CRCs, known input codes, channel identities, saved quality and the laptop’s actual decode state.

The image’s effective configuration and hashes are in `firmware/`. The task watchdog is enabled. The separate historical failed attempt with the watchdog disabled is explicitly labeled under `results/before-refinement/`; it is not the passing nominal image. Higher-priority ISR experiments were reverted.

Large serial exports are fixture overhead after recording. The runner’s current 120-second simulated export window replaces the original 30-second limit that truncated the low-battery UDP dump. The current web low-battery run completes both exports. CLI retry remains quota-dependent. Optional VCD acquisition should be a separate bounded capture: downloading it after a large export failed in the nominal run. Do not replace a missing trace or export with a pass.

`make_stimulus.py` produces the ngspice input deck, ideal quantized CSV and chip stimulus table. Its buffer is a documented 1 MHz closed-loop surrogate with assumed headroom, not a manufacturer op-amp model. Recompile `chips/ad7606.chip.c` with `wokwi-cli chip compile` after changing that table, then rebuild/hash the simulation image. The local [offline pipeline](../offline-pipeline/README.md) exercises these filtered signals without consuming cloud minutes.

## Evidence files

Each completed case contains a compressed serial log, sanitized CLI summary, original result, updated assessment, tested-build manifest, exact `.raw` bytes, explicitly synthetic `.afolog`, converted CSVs and a live receiver report. Original `.raw` metadata is preserved and may say `synthetic=false`; all files here originate from simulation. `.afolog` fixtures and companion documentation identify them correctly.

Wireless packet loss can remove END. The receiver must leave the ending unconfirmed rather than invent reason 0. The saved recording remains the independent reference. A quota refusal, transport error or partial export is recorded separately from a firmware failure.
