# Photo-based pin-map update

The supplied product photos identify header labels and their order. They do not establish continuity on a received module, its regulator wiring, or the installed mode straps. The 3D viewer now routes these connections to photo-ordered header positions instead of virtual terminal panels. Board envelopes and header pitch remain approximate; use the labelled photo map for assembly orientation.

Open [the header map with source photos](pinmap-evidence/header-map.html). The original images and machine-readable transcription are included in `pinmap-evidence/`. Local row/position numbers are documentation aids, not official connector numbering.

## GY-521 / MPU-6050

Orient the module **component side up**, header above the chip and `MPU-6050` lettering below. Left to right:

| Local position | Label | Foot module | Shank module |
|---|---|---|---|
| 1 | INT | GPIO16 | GPIO17 |
| 2 | AD0 | GPIO7, driven low → 0x68 | GPIO15, driven high → 0x69 |
| 3 | XCL | Not connected | Not connected |
| 4 | XDA | Not connected | Not connected |
| 5 | SDA | GPIO4 | GPIO4 |
| 6 | SCL | GPIO6 | GPIO6 |
| 7 | GND | Common ground | Common ground |
| 8 | VCC | Selected 3.3 V rail, subject to regulator-path check | Same |

XCL/XDA are the auxiliary bus, not the main SDA/SCL connections. The photo shows resistors marked `222` (nominal 2.2k), but does not establish which nets each resistor connects to. Trace and measure onboard pull-ups before fitting additional ones. Two modules may put their pull-ups in parallel; do not assume the effective value remains 2.2k.

Measure the MPU chip supply after the module regulator: it must remain within 2.375–3.46 V. Verify the actual pull-up rail and I2C rise time before using 400 kHz, especially with foot/shank cables. Header order is now identified; electrical suitability remains untested.

Source: [TDK MPU-6050 supply specification](https://product.tdk.com/en/search/sensor/mortion-inertial/imu/info?part_no=MPU-6050).

## Remaining scope

This update changes wiring tables, photo evidence and viewers only. Firmware, PCB copper and manufacturing files are unchanged. ADC configuration and electrical checks, auxiliary circuit hole allocation, USB VBUS access and unselected carriers remain release gates. Do not interpret photo-labeled endpoints as measured electrical validation.
