# Lab build guide

Use the package-specific staged guide for component values and numerical analog/power acceptance limits. Use the breadboard viewer's single-board mode for insertion holes and Exact wire endpoints for defined connections. Dashed links are conceptual only. Physical module header order must be verified before a corresponding lead is installed.

| Stage | Add | Evidence required before moving on |
|---|---|---|
| 1 | Power and dummy loads | Polarity, regulated voltage, ripple, startup and temperature |
| 2 | ESP32, controls, programming | Reset/programming, buttons/LEDs, current and USB detection |
| 3 | ADC, clock/reference | Identity/readback where supported, 8 kHz timing, known DC codes and fault evidence |
| 4 | First analog channel | Offset, scaling, frequency response, noise, clipping and unplugged bias |
| 5 | Remaining analog channels | Channel identity, supported 2/4 configurations, crosstalk and disabled-channel behavior |
| 6 | One IMU, then two | Identity, configuration, sample rate, axis signs and cable reliability |
| 7 | microSD | Continuous recording, conversion, full-card faults and interrupted-file recovery |
| 8 | Wi-Fi during recording | Explicit wireless gaps and no unexplained SD loss |
| 9 | Protected battery | Repeated startup/shutdown, 60-minute recording and measured two-hour runtime |
| 10 | MyoWare/wearable mounting | Movement artifacts, mechanical security, safety and approved participant procedure |

For MPU standalone diagnosis use diagnostic-imu-one and diagnostic-imu-two without ADC, SD or Wi-Fi. Require both addresses to return WHO_AM_I=0x68, chip supply 2.375–3.46 V, I²C rise time ≤300 ns at the intended cable length, 200 Hz ±2% over 60 s and zero bus/FIFO errors. Full details and pull-up instructions are in each MPU wiring guide.

Do not connect mains-powered instruments or charging cables while electrodes are attached. All instrument-connected bring-up uses synthetic signals, with no person attached. Do not order the compact board on the strength of ERC/DRC alone; complete staged results and final design review first.

Record date, board revision, firmware manifest/hash, instrument identification, settings, measured limits, pass/fail and corrective action for every test. Blank results are pending, never inferred passes.
