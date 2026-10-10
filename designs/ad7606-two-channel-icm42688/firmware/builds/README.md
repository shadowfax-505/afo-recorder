# Firmware builds

These profiles use source set **ad7606-2ch-1.7** (previous: 1.6). All seven were cross-compiled with ESP-IDF v5.4.2; their source and binary SHA-256 hashes are in `validation.json` and each profile's manifest. The laboratory binaries have not been flashed or executed on an assembled recorder. Wokwi used a separate instrumented image.

| Build stage | Profile | Hardware / dependencies |
|---|---|---|
| 2 | `diagnostic-controller` | Breadboard controller and controls; no ADC, IMU, SD or Wi-Fi required |
| 3–5 | `diagnostic-adc` | Breadboard controller and qualified AD7606; add analog paths progressively; no IMU, SD or Wi-Fi required |
| 6, first carrier | `diagnostic-imu-one` | Existing ADC stage plus foot ICM carrier; no shank, SD or Wi-Fi required |
| 6, both carriers | `diagnostic-imu-two` | Existing ADC stage plus both ICM carriers; no SD or Wi-Fi required |
| 7 | `breadboard-sd-only-2ch` | Both EMG paths, two IMUs and SDMMC; Wi-Fi off |
| 8–10 | `breadboard-record-2ch` | Complete breadboard with SD and best-effort Wi-Fi |
| Compact PCB only | `record-2ch` | PCB SD CMD GPIO38; do not flash this image to the GPIO47 breadboard |

Breadboard SDMMC uses **CMD GPIO47, CLK GPIO39, D0 GPIO40**. See [SD wiring](../../docs/sd-card-wiring.md), [short lab sequence](../../docs/lab-quickstart.html) and [applied simulation findings](../../docs/breadboard-refinements.html). Each build has exactly two EMG channels; there is no four-channel setting for this PCB.

Flash bootloader, partition table and application from one chosen profile, at that profile's manifest offsets: normally `0x0`, `0x8000`, `0x10000`. Keep the manifest and actual application hash with the measured run. Do not mix files from profiles, substitute a historical package or flash `simulations/integrated-recorder/firmware/merged.bin`.

Recording profiles hold no Wi-Fi password. On first boot the recorder generates a random 16-character password, stores it in NVS and prints it on the USB console at every boot (`Laptop AP: AFO-Recorder-B; password: …`). Read it once at the bench and keep it private; erasing flash creates a new one. The SD record queue holds 20,480 records (about 2.44 s) in PSRAM.

Diagnostics print the firmware identity in their first line. IMU lines report `interval_us`, `tick_step_mean` (expect 5000 at 200 Hz) and `host_us_per_tick` for the stage-6 timestamp-scale check. Diagnostics permit USB for synthetic tests, acquire in approximately one-second windows, then stop triggers while printing. Recording interlocks remain active. A diagnostic fault latches; correct the cause and restart. The GPIO21 pin is low when USB is attached; the printed attachment indicator is the inverse.

ADC configuration includes one discarded RESET-time read per invocation. Expect normally one at diagnostic initialization and two before the first recording session after boot. These are not saved samples. Current recording firmware checks BUSY acceptance and rejects late/unread/overlapping conversions rather than silently accepting stale data.
