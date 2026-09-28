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
