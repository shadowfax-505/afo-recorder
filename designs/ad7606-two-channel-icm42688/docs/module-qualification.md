# Module qualification before connecting ESP32 signals

These are required checks on the received hardware, not unresolved logical wire destinations. Photographs establish labels but cannot establish resistor population or internal continuity. Record readings and board revision. All checks use synthetic signals with no electrodes attached to a person.

## AD7606 / RoboticsBD RBD-3184

Use the [original AD7606 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf), not AD7606B register instructions. The three onboard conditions are PAR/SER high for serial mode (chip pin 6), STBY high for normal operation (pin 7), and REFSELECT high for internal reference (pin 34). These are not extra header wires. Confirm each by unpowered continuity/resistance to its selected rail, then by powered voltage with ESP32 disconnected.

Trace VIO to VDRIVE pin 23. Verify it is not hard-tied to 5 V. Supply module +5V with 4.75–5.25 V and VIO with 3.3 V; require VIO within 3.135–3.465 V before connecting ESP32. Check no output exceeds the ESP32 I/O rail. Logic input thresholds are ≤0.3×VDRIVE low and ≥0.7×VDRIVE high. The reference should be near 2.5 V (2.45–2.55 V is only a gross screening window).

Some similar boards select serial mode with R1/R2 near SP/8080 markings. Do not assume the supplied board's resistor arrangement: identify the chip-pin-6 node, VIO and ground with a meter. Only if the pads are confirmed as a pull-up/pull-down pair, remove the pull-down and install a 10 kΩ pull-up at the verified position. Never short unidentified pads. If the node cannot be safely accessed or its circuit verified, do not connect that module until a technician can qualify it.

Ground RANGE/RAGE for ±5 V and OS0–OS2 for no oversampling. Tie CVA/CVB together as listed. DB7 (chip pin 24) is serial DOUTA; DB8 (pin 25) is the unused second output. Ground only the unused parallel-input pins listed in the wire table after confirming serial mode; do not ground DOUTB. Verify BUSY and conversion/read timing with a logic analyzer at 8 kHz before signal tests. Read all expected words in channel order even when only two are exported.

The underside photo labels define CN1 orientation; a component-side view mirrors the header. Identify the GND/+5V end first. Do not infer orientation from the seller's unordered pin list. Unused analog inputs have the defined ground connections in the tables.

## GY-521 / MPU-6050

Use the [TDK MPU specification](https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/mpu-6000-datasheet1.pdf). The photographed component-side header is INT, AD0, XCL, XDA, SDA, SCL, GND, VCC left to right. XCL/XDA are unused. Supply VCC as shown, then measure the actual chip VDD: it must remain within 2.375–3.46 V. A regulator drop from 3.3 V may be acceptable only if measured within limits at load. Do not blindly change VCC to 5 V.

Identify onboard SDA/SCL pull-up resistors by continuity. Remove those pull-ups when installing the specified external 2.2 kΩ pull-ups to 3.3 V, so unknown parallel pulls do not overload the bus. Verify neither line is pulled to 5 V. At the configured 400 kHz, measure rise time ≤300 ns, logic-low ≤0.4 V and logic-high close to 3.3 V. If the chip rail fails, use qualified rework to isolate its regulator and supply verified 3.3 V directly to the chip supply node; verify every connection first and record this module-specific adaptation. Do not bridge an unidentified regulator.

Foot AD0 is GPIO7 low (0x68); shank AD0 is GPIO15 high (0x69), set before communication. INT uses GPIO16/17. Check WHO_AM_I, configuration readback, FIFO order/overflow and 200 Hz acquisition separately. Interrupt/reconstructed times are host estimates, not sensor timestamps.

## ICM-42688-P

The selected carrier is MIKROE-4237 6DOF IMU 14 Click; use its included manufacturer schematic/CAD evidence. Set SPI jumpers JP2–JP4 to 1–2 and 3.3 V operation. Use the listed mikroBUS connector pins, not the bare-chip pin numbers. SNC/unused synchronization is tied as listed; only configured INT1 is used. Confirm module identity and configuration before recording. Manufacturer model dimensions do not replace measurement of the received assembly.

## Supplies and bare MyoWare

Verify regulator VIN/GND/VOUT silkscreen and lead polarity before attachment. For bare MyoWare 2.0 use VIN, GND and RAW solder pads; ENV and RECT are different signals. Front and back views are mirrored. Follow the [MyoWare advanced guide](https://cdn.sparkfun.com/assets/learn_tutorials/1/9/5/6/MyoWare_v2_AdvancedGuide-Updated.pdf). USB, laboratory equipment and chargers remain disconnected during electrode-attached use.


### Acceptance hierarchy for this active build

The sequential build uses 3.23–3.43 V at VIO as the project target, measured at the module. Wider qualification windows elsewhere describe a gross check, not permission to skip this target or the ESP32 input-level check. AD7606 AVCC operating limits are 4.75–5.25 V; the project rail target is 4.80–5.20 V. Record meter uncertainty, startup peaks and loaded voltages. Midpoint acceptance is 0.49–0.51 times the actual analog rail, rather than an independent fixed nominal window.
