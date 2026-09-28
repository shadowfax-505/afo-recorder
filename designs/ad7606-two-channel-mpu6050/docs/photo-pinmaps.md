# Photo-based pin-map update

The supplied product photos identify header labels and their order. They do not establish continuity on a received module, its regulator wiring, or the installed mode straps. The 3D viewer now routes these connections to photo-ordered header positions instead of virtual terminal panels. Board envelopes and header pitch remain approximate; use the labelled photo map for assembly orientation.

Open [the header map with source photos](pinmap-evidence/header-map.html). The original images and machine-readable transcription are included in `pinmap-evidence/`. Local row/position numbers are documentation aids, not official connector numbering.

## AD7606 CN1 connections

Use the **underside view**, GND/+5V end at the top. “Inner” faces the board centre; “edge” faces the long board edge. Viewing the component side reverses the apparent order. Do not rely on wire colour alone.

| Signal | CN1 local location | Connect to |
|---|---|---|
| +5V | Row 1, edge | Regulated 5 V |
| GND | Row 1, inner | Common ground |
| VIO (photo reads VO/VIO) | Row 7, edge | 3.3 V only after continuity to chip VDRIVE pin23 and rail-isolation check |
| CVA and CVB | Row 4, edge and inner | Same GPIO11 trigger node |
| RD / SCLK | Row 5, inner | GPIO12 |
| RST | Row 5, edge | GPIO9 |
| BUSY | Row 6, inner | GPIO8 |
| CS | Row 6, edge | GPIO10 |
| DB7 / DOUTA | Row 11, inner | GPIO13 |
| OS0 | Row 2, edge | GND |
| OS1 | Row 2, inner | GND |
| OS2 | Row 3, edge | GND |
| RAGE / RANGE | Row 3, inner | GND for ±5 V |
| DB15 | Row 15, inner | GND after serial-mode verification |

**Additional serial-mode terminations:** DB0–DB6 and DB9–DB14 also go to ground. These were missing from the earlier named-terminal harness and are now included. Fit them only after confirming the module is in serial mode; grounding active parallel outputs can cause contention. DB7 is the selected serial output. Leave DB8/DOUTB and FRST unconnected for this single-data-output implementation.

The chip requires PAR/SER (chip pin6) high and DB15 low for serial mode. The photo shows an `SP/8080` resistor-selection area, but it does not establish which pad reaches pin6 or whether an installed resistor ties it low. **Do not bridge both pads or infer a resistor move from appearance.** With power off, trace the selector to pin6, VIO and GND; then confirm the intended mode with controlled power before ESP32 attachment. Check STBY pin7 high and REF SELECT pin34 high for normal operation and internal reference. These are module-configuration checks, not newly identified CN1 pins.

CN2 signal rows are identified in the component-side photo: V1–V8 have paired G pads. Connect EMG1 output to V1 and EMG2 to V2; expandable designs also connect EMG3/4 to V3/4. Ground the unused ADC inputs. In two-active-channel mode on a four-input board, retain the existing input bias networks on unused EMG circuits. Leave the separate VX pad disconnected until its purpose is verified.

Before connecting the ESP32: verify supply polarity and absence of VIO-to-5V ties. Measure 5 V supply within the chip's 4.75–5.25 V range; target VIO 3.3 V. Confirm BUSY and DOUTA logic levels are appropriate for the ESP32. A photo cannot prove any of these electrical conditions.

Source: [Analog Devices AD7606 datasheet, interface mode and pin descriptions](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf).

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
