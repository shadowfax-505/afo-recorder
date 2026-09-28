# Choosing an IMU version

Both families retain the same ADC and EMG channel configuration, 200 Hz foot/shank motion sampling, SD storage and best-effort Wi-Fi.

| Property | Original ICM-42688-P | Separate GY-521/MPU-6050 |
|---|---|---|
| Interface | SPI | Shared 400 kHz I²C |
| Device selection | Separate chip selects | Addresses 0x68 and 0x69 |
| Timing evidence | Sensor timestamp plus ESP32 interrupt | ESP32 interrupt and FIFO order; no sensor clock field |
| Timestamp alignment | Requires calibration | Estimated intervals; requires calibration |
| Module procurement | Exact carrier still pending | RoboticsBD GY-521 selected; purchased-board details unverified |
| Cable validation | SPI signal integrity | I²C capacitance, pull-ups and rise time |

Use the MPU version where local module availability is the priority. Neither version has measured synchronization, runtime or wearable safety validation. Do not mix the firmware, IMU cable functions or decoder assumptions between packages. Old ICM recordings remain readable by the new tools.
