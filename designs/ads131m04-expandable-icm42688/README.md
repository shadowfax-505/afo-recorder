# Project lead: Muttakin Rahman

Start with [the guided build](viewer/build.html). The [source and licence notices](THIRD_PARTY_NOTICES.md) distinguish project material from third-party assets.

> Current assembly entrypoint: [complete build guide](docs/build-guide.html), [module qualification](docs/module-qualification.md), and [current validation](docs/validation-report.md). Historical reports and stage overview drawings are retained for traceability.

# ADS131M04 · Two or four EMG channels — ICM-42688-P

**11 October 2026 firmware update (`dual-1.2`):** the SD record queue now holds 20,480 records (about 2.44 s) in PSRAM instead of 2,048 (0.244 s), which was shorter than the 250–500 ms write-busy time an SD card may legally take; no Wi-Fi password is compiled in: each recorder generates a random 16-character password on first boot, stores it in NVS and prints it on the USB console at every boot (`Laptop AP: AFO-Recorder-B; password: …`); read it once at the bench and keep it private; ICM-42688 FIFO timestamp ticks are converted as 32/30 µs (TDK ICM-426xx driver PLL scale), not 1 µs; the converter reads `imu_timestamp_tick_us` from the recording and adds an `imu_clock` screen; the live-metadata limit is 1,400 bytes, with a host test that compiles the real metadata for every profile. All profiles were rebuilt with ESP-IDF v5.4.2 and are cross-compiled only, not flashed or simulated. This package still uses the earlier recorder generation and does not include the later fixed-two corrections (worker lifecycle, BUSY confirmation, IMU clock continuity).

[Open the assembly viewer](viewer/index.html) · [Build guide](docs/staged-build-guide.md) · [Wiring guide](docs/breadboard-assembly.md)

This copy preserves the original ICM design behavior. Original package files remain separately preserved in outputs.

Serve this folder over HTTP; opening the viewer directly as a local HTML file will block asset fetches in most browsers. Standard filenames such as CMakeLists.txt, main.c, index.html and KiCad project members are retained for tool compatibility.

All hardware remains an engineering prototype pending physical validation. Module pin positions and outstanding wiring gates are documented; no board order is implied.
