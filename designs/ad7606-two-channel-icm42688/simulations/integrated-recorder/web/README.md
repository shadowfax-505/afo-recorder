# Run the integrated recorder in the web simulator

These files run the AD7606 / fixed two-channel / ICM-42688-P recorder on Wokwi's ESP32-S3. They are a **simulation fixture**, not hardware flashing files. The actual recorder code runs with modeled sensors, a PSRAM disk replacing SDMMC, and a loopback UDP subscriber replacing the laptop radio link.

1. Open the [official custom-firmware template](https://wokwi.com/projects/305457271083631168).
2. Replace `diagram.json` with this folder's copy. Import the six `.chip.c` / `.chip.json` files through the editor's **Upload File(s)** command. Retain the template's placeholder sketch; it is not used for this firmware run.
3. Focus an editor, press **F1**, and choose **Upload Firmware and Start Simulation…**. Select `../firmware/merged.bin` from the project package. This merged image includes the bootloader, partition table and application.
4. Allow recording and the post-recording export to finish. The serial monitor must contain `INTEGRATED_COMPLETE` and both `EXPORT_END` markers. A refusal case intentionally has no recording export. Copy the complete serial transcript into an evidence folder as `serial.txt`; include the diagram actually used and `../firmware/manifest.json` as `tested-build.json`.
5. From the parent folder, run `python3 assess_web.py --case normal --results /path/to/evidence`. The evidence folder contains a `normal/` subfolder. The script verifies diagram/model/image identity, checks the boot ELF identifier, requires complete byte exports, and uses the actual converter and live decoder. A partial dump, panic, wrong ADC code or hidden gap fails.

The [official firmware-upload instructions](https://docs.wokwi.com/guides/esp32#custom-application-firmware) and [custom-chip documentation](https://docs.wokwi.com/chips-api/getting-started) describe these supported interfaces. An account's CI quota is separate from a successful web-editor execution; do not label a refused CLI attempt as a pass.

For another case, use its saved `diagram.json` from `../results/web-current/`. `run.py` lists the fixture selectors and generates each configuration. Restart with a fresh firmware upload after changing a selector or fault attribute. Do not reuse a previous transcript under a new case name. The selector for ADC faults is shared; its distinct `fault` attribute identifies stuck-high BUSY, stuck-low BUSY or an ignored trigger.

`prepare_web.py` creates these files from the authoritative chip sources. The browser compiler could not resolve `stimulus.h` as an extra editor tab, so it is inlined into the ADC source. Its header-only `#pragma once` is removed, leaving a blank line. Model callbacks and stimulus values are unchanged. `manifest.json` records both source and web-file hashes. The CLI uses the original source and precompiled WASM; the browser compiles these C files itself.

Keep the original `.raw` exports and transcript. Derived `.afolog` files are explicitly marked synthetic; no participant data is used. Logic-analyzer download is a separate check. A successful serial/file run does not establish a captured VCD trace, physical timing, SD-card endurance, battery runtime or over-the-air Wi-Fi performance.
