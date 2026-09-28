# System architecture

MyoWare RAW outputs pass through protected, biased and filtered analog channels into a simultaneous-sampling ADC. An ESP32-S3 timestamps acquisitions, retains counters/fault evidence, buffers records for microSD and optionally forwards packets over Wi-Fi. Foot and shank modules provide six-axis motion readings.

The compact recorder is a single main PCB; motion sensors remain remote modules. Breadboard setups use a DevKitC-1 N8R8 and selected modules. Module power circuitry and analog package parasitics differ from the compact PCB and must be treated as fixture differences, not proof of identical noise or runtime.

## ADC alternatives

AD7606: 16-bit signed input readings, ±5 V range, 5 V analog power and 3.3 V interface, no oversampling initially. Drive both conversion inputs together and retain trigger timing. The chip has no serial-frame CRC; container CRC protects recorded bytes but cannot identify every ADC link error. The RoboticsBD HW-AD7606-F4 digital header map is still unverified.

ADS131M04: 24-bit simultaneous converter, external 8.192 MHz clock, configured decimation/filter and data-ready acquisition. CRC/status handling is ADC-specific. Lab carrier selection and input-loading equivalence remain dependencies.

## Motion-sensor alternatives

ICM packages retain their original SPI implementation and timestamp-bearing packets. MPU packages use shared GPIO4 SDA/GPIO6 SCL at 400 kHz, distinct addresses 0x68/0x69 and interrupts on GPIO16/17. GPIO7/15 drive address selection. MPU packets retain FIFO order, batch membership and ESP32 timing evidence; no sensor-clock field is fabricated.

Original ADC and EMG designs remain independent. All alternatives default to two active EMG channels. Only expandable packages permit four. Unused physical inputs never become valid muscle measurements in exported files.
