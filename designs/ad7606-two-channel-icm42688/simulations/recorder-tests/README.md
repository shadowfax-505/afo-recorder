# Recording and shutdown checks

Project lead: Muttakin Rahman

`python3 run.py` compiles the production `firmware/main/main.c` and `format.c` directly. It runs 19 cases for each of the PCB and breadboard profiles: **38 passing cases**. The test does not maintain a second implementation of the recorder.

The API shim supplies deterministic task states, queue results, filesystem responses, controls and synthetic sensor records. It checks early worker completion, task creation failure, queue overflow, USB inhibition, low battery, full-card handling, partial/zero/interrupted writes, sync failures, close failure and both IMU shutdown calls. Successful SD and Wi-Fi END records must be identical. The actual production metadata must fit the AFW1 packet and round-trip through the laptop decoder.

Results are in [results/summary.json](results/summary.json). Every published recording fixture is explicitly marked synthetic. The existing converter checks its original production record bytes and CRCs; the fixture header is relabeled to avoid presenting simulated input as a measured recording. Original unmarked capture bytes exist only in the temporary test directory and are removed after the run.

[Before-fix evidence](results/before-fix.json) records failures of the same assertions against the earlier recorder source. Native shims do not execute a FreeRTOS scheduler, concurrent cores, GPIO edges, SDMMC, radio or physical persistence. Sensor acquisition is covered separately by the Wokwi ADC/IMU package.

The `esp32/` project tests the production task lifecycle using real ESP-IDF FreeRTOS on a simulated ESP32-S3. Peripheral entry points are stubs. **Its image is for simulation only and cannot record from hardware.** It is separate from the seven firmware profiles used for laboratory construction.

An END marker among readable bytes cannot certify that a failed final sync or close persisted those bytes. The recorder therefore reports the final filesystem API result over best-effort Wi-Fi, and the physical procedure must check the error LED and recovered file after a stop. Neither a successful filesystem return nor a simulated test proves survival of arbitrary power loss.
