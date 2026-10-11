# ICM-42688-P register-level model

Project lead: Muttakin Rahman

`python3 run.py` compiles the production `firmware/main/sensors.c` and `imu_timing.h` and drives them through two models of the ICM-42688-P on the shared SPI bus (foot CS GPIO7, shank CS GPIO15). Set `AFO_NATIVE_SANITIZERS=1` to add ASan/UBSan. Results: [results.txt](results.txt), [results.json](results.json).

The model enforces rules taken from the official ICM-42688-P datasheet (DS-000347 revision 1.6) and cross-checked against TDK's ICM-426xx driver definitions and ArduPilot's flight-proven ICM-42688 driver:

- reset values and reserved bits of every register the firmware writes; reserved field codes (ODR, full scale, filter order, filter bandwidth, interface selection);
- no register access within 1 ms of power-up or soft reset; no register write within 200 µs of enabling the accelerometer or gyroscope; gyroscope on for at least 45 ms;
- INT_ASYNC_RESET cleared before INT1 is used; INT1 push-pull active-high for the ESP32 rising-edge input;
- FIFO packet 3 layout (header, big-endian accel and gyro, temperature, 16-bit timestamp), FIFO_COUNTH/L latching, whole-packet reads with partial-read resume disabled, FIFO full in stream mode, FIFO flush;
- accelerometer and gyroscope invalid markers (−32768) until their start-up times have passed;
- timestamp ticks of 32/30 µs (DS-000347 section 12.7) and an optional sensor clock error (the datasheet allows ±1.5 % at 25 °C, ±2 % over temperature).

Checks: identification and readback of every configuration write; SPI pins, mode 0 and 1 MHz; the final register state; 60 s of streaming per sensor with no header error, invalid sample or overflow; host-time estimates exact for an exact clock; clean stop; a 0.5 % sensor clock error producing the expected 300 ms per minute drift of the firmware estimate (corrected offline by `host_time_fitted_us`); a sensor with its jumpers in the I2C position failing identification; a register that ignores writes failing readback; an 800 ms polling stall reported as FIFO overflow.

This is evidence that the firmware follows the documented device rules. It is not a substitute for the stage-6 bench test: the received carriers' jumpers, wiring, signal integrity, sensor physics and actual clock must still be measured.
