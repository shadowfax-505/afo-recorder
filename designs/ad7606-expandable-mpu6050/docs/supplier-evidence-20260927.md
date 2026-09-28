> MPU variant: [mpu6050-wiring-and-timing.md](mpu6050-wiring-and-timing.md) is authoritative for sensor wiring, timing and current release gates. Inherited ADC/analog instructions remain applicable.

# Supplier evidence received 2026-09-27

The user supplied two top-side photographs of the RoboticsBD RBD-3184 AD7606 module and the seller function list. PCB marking HW-AD7606-F4 is visible. Analog input labels V1–V8 and adjacent G labels are visible. The separate Vx/GND pair is visible; Vx must not be assumed to be VIO or 5 V. The digital header labels are not readable in these views. The 4 × 3 × 2 cm figure is explicitly shipment dimensions, not verified PCB geometry.

The seller list confirms claimed interface functions, but omits a physical connector map, the serial-mode selection connection, and which module terminal carries DOUTA. IC pin numbers in module-verification.md are not module header numbers. These images do not release the digital harness. Required next evidence: clear underside/header-label photograph or exact HW-AD7606-F4 schematic, followed by powered-off continuity and interface-voltage checks.

MyoWare sourcing reference supplied by user: https://store.roboticsbd.com/biometrics-skin/3532-myoware-20-muscle-sensor-robotics-bangladesh.html . Bare MyoWare 2.0 remains selected. Vendor page retrieval returned HTTP 403; no new physical pad map was verified.

IMU candidate supplied by user: https://store.roboticsbd.com/robotics-parts/104-6dof-accelerometer-gyroscope-gy-521-mpu-6050-robotics-bangladesh.html . This is GY-521/MPU-6050, not GY-521/MPU-6050. Confirmation to change all three designs has been requested. Existing SPI driver, firmware and PCB connectors are not compatible merely by changing the model name. Vendor retrieval returned HTTP 403. No substitution has been made yet.

Verified chip-level reference: https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606_7606-6_7606-4.pdf . The AD7606 internal conversion clock does not remove the need for externally timed CONVST triggers and serial read clocks.
