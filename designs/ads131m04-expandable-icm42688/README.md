# Project lead: Muttakin Rahman

Start with [the guided build](viewer/build.html). The [source and licence notices](THIRD_PARTY_NOTICES.md) distinguish project material from third-party assets.

> Current assembly entrypoint: [complete build guide](docs/build-guide.html), [module qualification](docs/module-qualification.md), and [current validation](docs/validation-report.md). Historical reports and stage overview drawings are retained for traceability.

# ADS131M04 · Two or four EMG channels — ICM-42688-P

**12 October 2026 firmware update (`dual-1.5`):** the Wi-Fi live task now announces a new session (its metadata packet) before that session's first data packet. Earlier firmware could send a record dequeued just after the per-loop metadata check first, and the laptop receiver dropped it as an unknown session. `firmware/main/wifi_live.c` is now byte-identical to the fixed two-channel AD7606 / ICM design's `ad7606-2ch-1.12`, where the fix was found by and passes the 18-case Wokwi matrix; this package was not rerun in Wokwi (`dual-1.4` / `mpu6050-1.4` name the AD7606 supply-ramp release, which this ADS131M04 package does not need, so its identity moves from 1.3 to 1.5 to stay aligned with the other designs). All profiles were rebuilt with ESP-IDF v5.4.2 and host tests pass; cross-compiled only, not flashed or simulated.

**11 October 2026 firmware update (`dual-1.3`):** the SD record queue now holds 20,480 records (about 2.44 s) in PSRAM instead of 2,048 (0.244 s), which was shorter than the 250–500 ms write-busy time an SD card may legally take; no Wi-Fi password is compiled in: each recorder generates a random 16-character password on first boot, stores it in NVS and prints it on the USB console at every boot (`Laptop AP: AFO-Recorder-B; password: …`); read it once at the bench and keep it private; ICM-42688 FIFO timestamp ticks are converted as 32/30 µs (TDK ICM-426xx driver PLL scale), not 1 µs; the converter reads `imu_timestamp_tick_us` from the recording and adds an `imu_clock` screen; the live-metadata limit is 1,400 bytes, with a host test that compiles the real metadata for every profile. All profiles were rebuilt with ESP-IDF v5.4.2 and are cross-compiled only, not flashed or simulated. Firmware `dual-1.3` (same day) also ports the corrections from the fixed-two AD7606/ICM recorder: the ADS131M04 keeps its DRDY interrupt, now allocated on the acquisition core; recording tasks are suspended and then joined and deleted by the recorder, so an early fault cannot free a task the recorder still uses; any fault stops acquisition; both IMU stop calls are attempted; queued data is synced before the END record, and the Wi-Fi stop verdict is sent only after the final write, sync and close checks; diagnostics acquire in one-second windows and stop triggers while printing; the IMU waits up to 100 ms for its first interrupt; ICM-42688 host times follow the sensor counter after one anchor (no re-anchoring jumps). The fixed-two native recorder harness (19 fault and lifecycle cases) passes for every profile of this package under ASan/UBSan.

[Open the assembly viewer](viewer/index.html) · [Build guide](docs/staged-build-guide.md) · [Wiring guide](docs/breadboard-assembly.md)

This copy preserves the original ICM design behavior. Original package files remain separately preserved in outputs.

Serve this folder over HTTP; opening the viewer directly as a local HTML file will block asset fetches in most browsers. Standard filenames such as CMakeLists.txt, main.c, index.html and KiCad project members are retained for tool compatibility.

All hardware remains an engineering prototype pending physical validation. Module pin positions and outstanding wiring gates are documented; no board order is implied.
