# Rebuilding the recorder firmware

The released builds use ESP-IDF v5.4.2 and the ESP32-S3 target. Activate that ESP-IDF environment first. Open a terminal in the chosen design's `firmware` folder. The ADC and IMU identities come from that package's sources; changing the EMG count does not change the sensor driver.

For a two-channel breadboard recorder with Wi-Fi:

```sh
idf.py -B build-breadboard-2 -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=breadboard -DAFO_WIFI=1 -DAFO_DIAGNOSTIC_STAGE=0 -DAFO_IMU_COUNT=2 build
```

For a two-channel custom-PCB recorder:

```sh
idf.py -B build-pcb-2 -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=pcb -DAFO_WIFI=1 -DAFO_DIAGNOSTIC_STAGE=0 -DAFO_IMU_COUNT=2 build
```

Only the expandable packages accept `EMG_CHANNEL_COUNT=4`. Use a separate build directory for each hardware/count combination. Set `AFO_WIFI=0` to isolate storage testing. Breadboard builds define `AFO_BREADBOARD=1` internally and use GPIO47 for SD CMD; PCB builds use GPIO38. Do not override this macro manually.

For a one-IMU bench diagnostic:

```sh
idf.py -B build-imu-one -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=breadboard -DAFO_WIFI=0 -DAFO_DIAGNOSTIC_STAGE=6 -DAFO_IMU_COUNT=1 build
```

Stage 2 checks the controller; stage 3 checks ADC communication; stages 4/5 cover analog input checks; stage 6 selects IMU diagnostics. These builds do not mount SD or start Wi-Fi. Power tests are instrument procedures, not firmware diagnostics.

Flash the selected build with ESP-IDF using the correct serial port, or use the offsets recorded in the release manifest with its accompanying bootloader, partition table and application. Do not mix binaries across variants. Programming and all instrument-connected tests must be performed without a person attached.

A successful build establishes compilation only. Verify the hardware identity, active channels and SD GPIO metadata in a synthetic bench recording before collecting measurements. See [SD wiring](sd-card-wiring.md) and [lab stages](breadboard-assembly.md).
