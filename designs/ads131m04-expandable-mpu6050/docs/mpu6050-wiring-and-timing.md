# MPU-6050 variant: wiring, timing and validation

This is a separate derivative using two RoboticsBD GY-521/MPU-6050 modules. The three original ICM-42688-P packages are preserved. ADC and EMG circuitry, channel counts and 8 kHz sampling are unchanged. Remote IMUs are ready-made modules, not new custom daughterboards.

## Named-terminal wiring

| Function | ESP32 GPIO | Recorder J3 foot / J4 shank pin | GY-521 silkscreen terminal |
|---|---:|---:|---|
| Module supply | regulated 3V3D | 1 | VCC, subject to rail test below |
| Ground | GND | 2 | GND |
| I²C clock | 6 | 3 | SCL on both modules |
| I²C data | 4 | 4 | SDA on both modules |
| Reserved | 5 | 5 | **Leave disconnected** |
| Foot address | 7, driven low | J3.6 | AD0, address 0x68 |
| Shank address | 15, driven high | J4.6 | AD0, address 0x69 |
| Foot interrupt | 16 | J3.7 | INT |
| Shank interrupt | 17 | J4.7 | INT |
| Additional ground | GND | 8 | Ground return if used |

Do not connect XDA/XCL (auxiliary bus). Do not hard-strap AD0 to a rail when using GPIO-driven address selection. Firmware establishes both addresses before its first transaction. WHO_AM_I must read 0x68 at **both** addresses; the register does not change to 0x69 on the shank. Existing 10k address pull-ups remain on the recorder PCB; GPIO7 overrides the foot pull-up low. GPIO5 remains reserved, not an I²C input.

These are verified recorder connector functions and named module terminals, **not a numbered GY-521 physical header map**. Exact purchased-board pin order, regulator, pull-ups and dimensions must be inspected. The viewer's GY-521 geometry remains illustrative. No physical header order is invented.

## Supply and I²C gate

Initially test with a current-limited 3.3 V supply and no person attached. Measure the MPU chip supply after any module regulator: it must remain within 2.375–3.46 V through startup and operation. Target 3.0–3.3 V. If the carrier cannot meet this on its VCC input, stop and document a board-specific regulator bypass or suitable carrier; do not automatically change VCC to 5 V.

Trace all SDA/SCL pull-ups with power disconnected. They must terminate at a verified 3.3 V-compatible logic rail, never 5 V. Fit or adjust one effective pull-up network for the combined bus: start at 2.2k to 3.3 V on each line and account for parallel onboard resistors. The main PCB relies on this **external module/harness pull-up network**; this dependency is intentional and must appear in the assembly BOM. Do not assume ESP32 internal pull-ups suffice (disabled in this driver).

At the full intended cable length, verify 400 kHz operation, 30–70% rise time ≤300 ns, low ≤0.4 V and stable ACKs from 0x68/0x69. Target high near 3.3 V and verify against the measured module logic supply's input limits. Keep wires short and pair each signal with a ground return. No fixed maximum cable length is claimed. Failure means the current harness fails release; it is not permission to silently lower bus speed without recording the change.

## Acquisition and format

- DLPF_CFG=3, SMPLRT_DIV=4: nominal 200 Hz. Accel range ±16 g (2048 LSB/g), gyro ±2000 dps (16.4 LSB/(degree/s)). Nominal filter bandwidths are 44 Hz accel and 42 Hz gyro; filter delay is not corrected.
- FIFO_EN=0x78 stores 12 big-endian bytes: accel XYZ then gyro XYZ. No temperature or sensor timestamp is fabricated. Check the 1024-byte FIFO for overflow before and after reads. Bus failure or overflow stops recording visibly; raw counter/status evidence remains in the file.
- New record types **8=MPU foot**, **9=MPU shank**, payload 40 bytes. First 12 bytes are original FIFO bytes; bytes 12–13 are little-endian batch index and 14–15 batch count. Three little-endian uint64 values follow: read start, read end, latest IRQ anchor in ESP32 microseconds. Container CRC and 64-byte record length stay unchanged. Types 2/3 remain legacy ICM packets.
- Metadata identifies MPU6050, I²C addresses, packet format, filter/divider, scaling and `irq-anchor-nominal-period-estimate`. Sensor timestamp tick is null. ADC-specific schema remains /2 or /3; record type and IMU metadata disambiguate the format.
- Timestamp each interrupt. Estimate FIFO sample times backwards from the latest interrupt at nominal 5000 µs spacing. Every MPU sample carries TIMING_UNCERTAIN. Interrupt/count disagreement, underflow or an interrupt arriving during the read adds GAP (possible loss or timing ambiguity, not proof of physical loss). Missing interrupts beyond 100 ms abort the session.
- CSV sensor timestamp, temperature and FIFO-header columns are blank for MPU data. Batch index/count are retained. The converter and live receiver continue reading legacy ICM recordings. Simultaneous EMG remains simultaneous; the two IMUs have independent clocks.

## Staged acceptance

1. Complete supply and bus electrical gates above with one module, then two. Address scan must identify exactly the intended responding devices; verify identity/configuration readback and address selection after reset.
2. Run diagnostic-imu-one, then diagnostic-imu-two. These builds need no ADC, SD or Wi-Fi. Over 60 seconds require 200 Hz ±2%, zero read errors and FIFO overflows. This is a project acceptance target, not a claim of measured oscillator accuracy.
3. Stationary test: acceleration magnitude 0.9–1.1 g, gyro each axis within ±5 degrees/s before calibration. Rotate known axes individually and record orientation/sign mapping; repeat with foot/shank cables exchanged to catch identity errors.
4. Logic-analyzer test: capture both INT lines, I²C, and EMG conversion/data-ready reference. Measure IRQ capture latency, jitter, independent-clock drift and filter delay under idle, SD and SD+Wi-Fi load. Preserve traces and report measured distributions. Do not claim millisecond synchronization from software tests.
5. Disconnect a sensor, hold a bus line low and induce FIFO overrun. Require visible faults or explicit gaps, never invented samples. Repeat 60-minute storage, Wi-Fi load and two-hour battery-runtime tests on the final assembly; these remain unperformed.

Compact-PCB ERC/DRC and exports are regenerated for this variant. Copper topology is retained while nets and connector functions change to I²C/address selection. Main-board power, USB-inhibit and ADC module wiring gates remain applicable. Breadboard firmware uses GPIO47 for SD CMD to avoid the V1.1 RGB LED. PCB firmware retains GPIO38. See sd-card-wiring.md; physical SD operation remains untested.

Sources: [TDK MPU-6050 specification](https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/mpu-6000-datasheet1.pdf), [Adafruit register definitions](https://github.com/adafruit/Adafruit_MPU6050), [selected carrier](https://store.roboticsbd.com/robotics-parts/104-6dof-accelerometer-gyroscope-gy-521-mpu-6050-robotics-bangladesh.html). Seller carrier pin layout/regulator circuit remains unverified. No physical measurements or human recordings have been performed by this implementation.
