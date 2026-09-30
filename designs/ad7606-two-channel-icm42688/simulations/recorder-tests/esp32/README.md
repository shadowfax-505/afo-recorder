# ESP32-S3 task lifecycle simulation

**Simulation only. Do not use this firmware for the laboratory recorder.** Sensor and Wi-Fi entry points are stubs; the seven real construction profiles remain in `firmware/builds/` at the design root.

The test includes the production recorder source directly, with its hardware entry point renamed. It executes the actual EMG/IMU tasks, fault latch, completion suspension and owner cleanup on real ESP-IDF v5.4.2 FreeRTOS in Wokwi. Each family completes 100 cycles: immediate normal stop, faulted workers already suspended before join, and an EMG-only task set with the absent IMU completion bit supplied.

All **300 cycles pass**. [Execution summary](results/summary.json), [serial evidence](results/serial.txt) and [CLI output](results/cli.txt) identify the tested source and ELF/merged-image hashes. The first harness waited only 10 ms for a worker with a 20 ms notification timeout; that [failed attempt](results/before-harness-wait-fix/README.md) is retained separately. The corrected test uses completion/state conditions with a 100 ms deadline. The production recorder already waits for suspension before deletion.

To rebuild, activate your ESP-IDF v5.4.2 shell, change into this directory and run:

```sh
python3 build_firmware.py
```

Install Wokwi CLI, provide its token through your local environment, then run:

```sh
python3 run_wokwi.py
```

`WOKWI_CLI` may select an executable outside PATH. No credential belongs in the project. The runner requires fresh serial output, all three family markers, the completion marker and exit code zero; an assertion/panic fails the result.

This tests RTOS control flow on an emulated ESP32-S3. It does not test ADC/IMU signals, SDMMC, Wi-Fi radio, power, physical timing or endurance. The [separate sensor simulation](../../wokwi/README.md) and [native filesystem/control cases](../README.md) cover their own documented scopes.
