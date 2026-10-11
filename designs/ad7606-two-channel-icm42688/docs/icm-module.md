# Selected ICM module

Two **MIKROE-4237 / 6DOF IMU 14 Click** boards replace the unselected carrier. Procurement and received revision remain unconfirmed. [Manufacturer reference](https://www.mikroe.com/6dof-imu-14-click).

Use 3.3 V. Set JP2, JP3, JP4 to SPI (pads 1–2). With component side up, AN at upper left and PWM/SNC at upper right: left column descends 1–8; right column descends 16–9. Numbers here are mikroBUS numbers, not chip pins.

| Header | Foot | Shank |
|---|---|---|
| 3 CS | GPIO7 | GPIO15 |
| 4 SCK | GPIO6 | GPIO6 |
| 5 MISO | GPIO5 | GPIO5 |
| 6 MOSI | GPIO4 | GPIO4 |
| 7 3.3V | 3V3D | 3V3D |
| 8 GND | GND | GND |
| 15 INT | GPIO16 | GPIO17 |
| 16 SNC | jumper to 9 GND | jumper to 9 GND |

Leave other headers unconnected. Keep INT2 disabled. The schematic grounds chip reserved pin 7; the user's chip sketch is not a carrier header map.

Geometry comes from the manufacturer v100 CAD. Its mesh envelope is 25.78 × 42.93 × 12.19 mm including headers, differing from the listing's size. Header centres are taken from DXF, but confirm board revision and dimensions before making a mounting template. The carrier adds a power LED and interface-selection circuitry absent from the bare-chip circuit; account for their current in runtime measurements.

## What has been verified without hardware (11 October 2026)

- **Carrier schematic (MIKROE 6DOF IMU 14 Click v100):** the ICM-42688-P VDD and VDDIO come only from mikroBUS 3.3 V (no regulator or level shifter). With JP2–JP4 at 1–2, MISO, SCK and MOSI reach the chip; CS goes directly to AP_CS; INT goes to INT1. mikroBUS PWM/SNC is pin 9 (INT2/FSYNC/CLKIN), which the datasheet says to ground when FSYNC is unused, as the wiring does.
- **Register configuration:** every address and value the firmware writes was checked against the official datasheet DS-000347 revision 1.6 register descriptions, TDK's ICM-426xx driver definitions and ArduPilot's flight-proven ICM-42688 driver (which uses the same `(header & 0xFC) == 0x68` packet check). Reserved bits keep their reset values; INT_ASYNC_RESET is cleared; I2C is disabled for the shared SPI bus.
- **Official datasheet cross-check (DS-000347 rev 1.6):** register reset values and fields; packet 3 byte layout and header table; invalid-sample marker −32768 with FIFO_HOLD_LAST_DATA_EN = 0; FIFO_COUNTH latching; 4-wire SPI timing (24 MHz maximum, 39 ns CS setup, SDO released within 28 ns of CS rising, which keeps the shared MISO free); input/output levels at 3.3 V; supply 1.71–3.6 V (absolute maximum 4 V); gyro 30 ms and accel 10 ms start-up; 100 µs INT pulse. Section 12.3's SPI-mode settings (DRIVE_CONFIG 0x05, INTF_CONFIG4 I3C_BUS_MODE 0, INTF_CONFIG6 I3C enables 1/1/1) are the reset values, which the firmware's soft reset restores.
- **Register-level model:** the production driver passes the [ICM-42688-P model test](../simulations/icm-register-model/README.md) with no datasheet-rule violation, including the 1 ms reset wait, the 200 µs power-on write blackout, whole-packet FIFO reads, 60 s of streaming per sensor and the fault cases (I2C jumper position, stuck register, FIFO overflow).
- **Timing:** FIFO timestamp ticks last 32/30 µs (DS-000347 section 12.7, Timestamp Interval Scaling), and the sensor clock may be off by up to ±1.5 % at 25 °C and ±2 % over temperature (Table 4). That clock error also scales the gyroscope rate reading unless calibrated. The firmware estimate follows the sensor clock, so use `host_time_fitted_us` from the converter to align IMU with EMG.

What remains physical: the received boards' identity and jumper positions, wiring and contact quality, signal integrity on the breadboard, the actual sensor clock and tick scale, sensor noise and bias, and axis signs. The IMU-only bench builds `diagnostic-imu-bench-one` / `-two` test all of these on the DevKit as soon as the carriers arrive, with explicit PASS/FAIL lines.
