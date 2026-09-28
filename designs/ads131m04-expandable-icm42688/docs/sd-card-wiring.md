# SD card wiring and firmware selection

This revision assigns **GPIO47 to SD CMD on the ESP32-S3-DevKitC-1 breadboard setup**. The custom PCB still uses GPIO38. This is a documented fixture difference; the ADC and analog circuits are unchanged. Original source packages are preserved. Use the current organized release for this correction.

The DevKitC-1 V1.1 onboard RGB LED uses GPIO38. GPIO47 is available on J3.17, while N8R8 reserves GPIO35–37 for memory. The breadboard must not use GPIO47 for expansion SDA at the same time.

## Connections

Use the Adafruit 4682 microSD breakout, not a similarly labelled 5 V adapter. JP1 numbers below refer to the manufacturer Eagle connector; match the printed signal names and connector orientation before applying power.

| Function | DevKit terminal | SD terminal |
|---|---|---|
| SD clock | J3.9 / GPIO39 | JP1.3 / SCLK |
| SD command | J3.17 / GPIO47 | JP1.5 / DI (CMD) |
| SD data 0 | J3.8 / GPIO40 | JP1.4 / DO (DAT0) |
| Ground | J3.22 / GND | JP1.2 / GND |
| Supply | Verified regulated 3.3 V rail | JP1.1 / 3V3 |

This uses the SDMMC peripheral in one-bit mode; DI is CMD rather than SPI MOSI. Keep the breakout's specified pull-ups. Do not substitute 5 V logic. The supply endpoint is identified electrically here; its physical regulator/header mapping must be verified separately. Do not join a USB-powered DevKit supply to an external regulator output.

## Select the build

- `breadboard-record-2ch`: GPIO47 CMD, SD and Wi-Fi.
- `breadboard-sd-only-2ch`: GPIO47 CMD, Wi-Fi disabled for initial storage checks.
- `breadboard-record-4ch`: GPIO47 CMD; available only for expandable EMG versions.
- `record-2ch` and `record-4ch`: custom PCB with GPIO38 CMD.

Firmware manifests include the three SD GPIO assignments. New recordings include `sd_cmd_gpio`, `sd_clk_gpio` and `sd_d0_gpio` metadata. Earlier diagnostic binaries remain available; those diagnostics do not mount SD. Do not select older snapshot recording binaries for the revised breadboard wiring.

## Stage-7 lab check

Use synthetic inputs with no person attached. First verify power-off continuity from each named terminal and absence of shorts to adjacent pins. Before inserting a card, measure 3.3 V at the breakout; the stage-1 regulated-rail target is 3.20–3.40 V. Confirm the actual module's permitted rail range before powering it.

Start with the SD-only build, then repeat with Wi-Fi enabled. A successful gate requires valid metadata identifying the selected hardware and GPIOs, a convertible recording, and zero unexplained sequence loss in a 60-minute recording. Test card removal, full-card refusal/error reporting and interrupted-file recovery under the existing storage procedure. Capture rail droop and signal levels during writes; investigate resets or errors before continuing.

Cross-compilation and viewer endpoint checks do not establish card compatibility, current capacity, signal integrity or sustained hardware throughput. Those measurements remain pending.

## Sources

- [Espressif DevKitC-1 V1.1 guide and J3 pin table](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)
- Adafruit 4682 manufacturer Eagle board, recorded in each package’s `docs/module-model-evidence.json`. Confirm the exact board revision; do not infer a substitute board’s pin order.
