# Project lead: Muttakin Rahman

Start with [the guided build](viewer/build.html). The [source and licence notices](THIRD_PARTY_NOTICES.md) distinguish project material from third-party assets.

> Current assembly entrypoint: [complete build guide](docs/build-guide.html), [module qualification](docs/module-qualification.md), and [current validation](docs/validation-report.md). Historical reports and stage overview drawings are retained for traceability.

# AD7606 · Two EMG channels — MPU-6050

**11 October 2026 firmware update (`mpu6050-1.2`):** the SD record queue now holds 20,480 records (about 2.44 s) in PSRAM instead of 2,048 (0.244 s), which was shorter than the 250–500 ms write-busy time an SD card may legally take; no Wi-Fi password is compiled in: each recorder generates a random 16-character password on first boot, stores it in NVS and prints it on the USB console at every boot (`Laptop AP: AFO-Recorder-B; password: …`); read it once at the bench and keep it private; the live-metadata limit is 1,800 bytes: this package's session metadata (about 1,360–1,430 bytes) exceeded the previous 1,280-byte limit, so earlier firmware silently disabled the Wi-Fi preview. All profiles were rebuilt with ESP-IDF v5.4.2 and are cross-compiled only, not flashed or simulated. This package still uses the earlier recorder generation and does not include the later fixed-two corrections (worker lifecycle, BUSY confirmation, IMU clock continuity).

[Open the assembly viewer](viewer/index.html) · [Build guide](docs/staged-build-guide.md) · [Wiring guide](docs/breadboard-assembly.md)

[MPU wiring, timing and limits](docs/mpu6050-wiring-and-timing.md) · [Validation report](docs/validation-report.md)

Serve this folder over HTTP; opening the viewer directly as a local HTML file will block asset fetches in most browsers. Standard filenames such as CMakeLists.txt, main.c, index.html and KiCad project members are retained for tool compatibility.

All hardware remains an engineering prototype pending physical validation. Module pin positions and outstanding wiring gates are documented; no board order is implied.
