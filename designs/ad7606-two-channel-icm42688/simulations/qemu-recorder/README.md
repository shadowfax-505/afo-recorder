# Offline ESP32-S3 integration experiment

This fixture runs the current recorder on Espressif QEMU. It provides additional startup and refusal evidence, **not a qualified 8 kHz integration result**. No physical hardware was used. Never flash the simulation image onto a recorder.

The current seven-case ledger retains four assessor passes and three failures. Three passes demonstrate explicit initialization refusal for unavailable storage, insufficient card space and an absent shank IMU. The stuck-BUSY run stops abnormally without accepting EMG; its ADC timeout path is not separately established because emulator scheduling can cause the same timing stop. Both stuck-low/ignored-trigger cases fail the stricter ADC-error gate. They contain no EMG, but do not demonstrate the intended fault path. The nominal run stops with reason 6 before accepting EMG, so this fixture cannot qualify continuous acquisition.

[Result ledger](results/current/summary.json) · [compiled source and image manifest](firmware/manifest.json).

## Scope

The Xtensa ESP32-S3 CPUs execute the actual ESP-IDF FreeRTOS, recorder control, ADC/ICM drivers, serializer, FatFS, Wi-Fi packet queues and lwIP loopback. QEMU does not provide this board's SPI, SDMMC, Wi-Fi, USB or GPIO-matrix devices. SPI functions therefore use behavioral C models; a timer ISR supplies IMU interrupt notifications; the original integration fixture supplies sparse PSRAM storage, battery/control inputs and a UDP-loopback subscriber. Wi-Fi radio SDK calls and an internal-ADC calibration constructor are substituted. The console uses UART rather than USB. These substitutions are documented in `main/model.c`, `main/fixture.c` and the compiled manifest.

The ADC model retains its nominal 4 microsecond BUSY interval. The production 1 microsecond BUSY-high observation and 125 microsecond conversion period remain unchanged. This emulator/fixture has not qualified those deadlines. Failure is retained rather than extending model timings until a nominal run passes. [Espressif QEMU feature matrix](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/README.md) · [ESP32-S3 usage and octal PSRAM](https://github.com/espressif/esp-toolchain-docs/blob/main/qemu/esp32s3/README.md).

## Startup correction

An exploratory QEMU run exposed startup stack overflow. The compiler had inlined session buffers into the startup function, also used by NVS/network initialization. Keeping `record_session` separate reduces the recorder startup's compiler frame from 2,640 to 352 bytes. The default main stack remains 8 KiB. This is not measured peak hardware stack usage; QEMU adds its own fixture frames. All seven laboratory profiles were rebuilt and the 38 native recorder-control cases passed after this change.

## Reproduce

Use the official Espressif ESP32-S3 QEMU runtime with octal PSRAM support. The recorded run used version 9.2.2-20260417. Set up the ESP-IDF 5.4.2 environment, then build:

```sh
python3 build_firmware.py --build-dir /absolute/path/to/qemu-build
```

Run a bounded case with a fresh copy of the flash image:

```sh
python3 run.py --qemu /absolute/path/to/qemu-system-xtensa \
  --image firmware/qemu-flash.bin --out /absolute/path/to/new-results \
  --case storage-mount-failure --case full-card-refusal --case absent-shank \
  --case adc-stuck-busy --case adc-busy-stays-low \
  --case adc-trigger-ignored --case normal
```

The mixed matrix intentionally returns a failure exit status. Each case saves the exact build manifest, command, original serial output, decoded recording where available and its assessment. An incomplete run also attempts a QMP CPU-state snapshot. An incomplete export, assertion, panic or conversion error cannot count as a pass. No elapsed emulator time is a measured MCU throughput, SD or radio benchmark.
