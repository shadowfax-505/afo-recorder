# Complete recorder scene for Wokwi

Project lead: Muttakin Rahman · AD7606 · two EMG inputs · two ICM-42688-P sensors

This scene puts the entire recorder on the canvas. It adds the protected battery, regulated rails, voltage/USB sensing, two MyoWare RAW paths and their frontends, status LEDs, start/stop control, storage and laptop preview around the tested ESP32-S3/ADC/IMU fixture.

## Run it

1. Open the [complete recorder project](https://wokwi.com/projects/476662256690643969). This saved project includes all 36 parts, 79 connections and 24 custom-chip files. The earlier vendor-template URL does not contain the recorder.
2. Download and extract [full-system-wokwi.zip](full-system-wokwi.zip). It contains the scene, simulation firmware, provenance manifests and firmware licence notices, with the folder structure preserved.
3. In an editor, press **F1**, choose **Upload Firmware and Start Simulation…**, and select `integrated-recorder/firmware/merged.bin` from the extracted bundle (`../firmware/merged.bin` relative to this folder). The placeholder sketch is not the recorder. The simulator must boot ESP-IDF v5.4.2 and identify ELF prefix `aabb34031`.
4. In the simulation's three-dot menu, select **Full screen**, then **Fit**. `Alt+Enter` and `F` are the displayed shortcuts. This frames all modules; zoom in to inspect individual interfaces.
5. Let the automatic nominal recording and export finish. Expected markers are `INTEGRATED_COMPLETE,case=0` and complete `EXPORT_END,AFO` / `EXPORT_END,UDP` lines. The known inputs are about 1 V and 2 V. Only EMG1/2 are exported; both IMU identities must be present.

Custom firmware upload is session state. A page reload may restore the placeholder image. Re-upload the merged image after reopening; pressing the default Play button alone is not the tested recorder run. The complete scene was saved successfully through Wokwi's Save a Copy command. Its persistence does not establish persistence of a custom firmware upload.

To reconstruct the project from scratch, open the [vendor template](https://wokwi.com/projects/305457271083631168), replace `diagram.json` with this folder's copy, and use the editor file menu → **Upload file(s)…** for every `.chip.c` and `.chip.json` file here. Wait until no **Missing chip** blocks remain. Replace the placeholder sketch with `esp32-bin-file.ino`, then perform the same firmware upload.

## Verified expanded scene

The complete scene finished an actual nominal web-simulator run with the current instrumented recorder image: **10,041 EMG frames, 263 foot records and 252 shank records**, with zero reported saved-queue drops, ADC errors or IMU errors. The strict assessor checks the boot image, original protocol sources, exact drawing, exported bytes, converter quality and live decoder. [Nominal result](results/normal/result.json) · [Scene checks](scene-checks.json) · [Saved canvas](browser-proof.png).

An independent fresh opening of the saved public project confirmed all models were retained and its diagram matches this folder exactly. The repeated [saved-project nominal run](results/saved-project-normal/result.json) also passes with the same saved counts. [Browser checks](browser-checks.json).

This new evidence covers the nominal case. The [eighteen fault/nominal cases](../results/web-current/summary.json) used the original smaller protocol fixture, retained unchanged. Neither drawing claims physical or research-quality validation. Nominal preview loss remains explicit; it does not alter the complete saved stream.

## Read the drawing

| Part | What this run actually tests |
|---|---|
| ESP32-S3, AD7606, two ICM devices | Actual recorder image, SPI, timers, interrupt handling, queues, serialization and behavioral sensor callbacks |
| MyoWare and two analog frontends | Passive illustrations. ADC codes are generated inside the behavioral ADC. RC/buffer behavior is assessed separately in ngspice. |
| Battery, regulators, voltage sensing and USB inlet | Passive power/interface illustrations. Fixture supplies battery and USB states; no electrical power or USB transport solver. |
| microSD block and its CLK/CMD/D0 connections | Correct lab SDMMC pin context. Real FatFS uses a PSRAM medium; no SDMMC/card execution. |
| ESP32 Wi-Fi and laptop blocks | Logical link illustration. Actual production UDP is received by an internal loopback subscriber; real laptop socket/browser checks are separate. |
| Button and LEDs | LEDs are connected to production outputs. The fixture automatically controls this short recording; the button is not claimed as an independently qualified control. |

Green/orange lines are executed sensor interfaces. Purple shows the illustrated analog path. Red/black are ideal supply context. Gray marks substituted SDMMC/USB/sense interfaces. Blue is a logical UDP link, not a physical cable. Logic-analyzer taps and the scenario selector are connected but hidden to keep the overview readable.

The added `AIN1`, `AIN2`, supply and ground pins are passive drawing ports, not RoboticsBD header numbering. Use the [physical assembly guide](../../../viewer/index.html?stage=10) and qualified module terminals for implementation.

In the complete project checkout, `build_scene.py` reproduces the drawing and copies the original protocol C sources byte for byte. `verify_scene.py` checks every original connection, the added lab GPIO assignments, frozen C sources and context-model boundaries. `assess_scene.py` checks the saved transcript with the existing converter and live decoder. These helpers need the complete project, not just the small scene/firmware download. The original eighteen-case diagrams and evidence are retained unchanged. An expanded drawing must not be described as a new analog, card or radio validation.
