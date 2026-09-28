# Selected laboratory parts — current implementation

|Function|Selected part|Boundary|
|---|---|---|
|Controller|ESP32-S3-DevKitC-1 N8R8|Use matching breadboard firmware; SD CMD is GPIO47|
|Protected battery|Adafruit 328, 1S 2500 mAh|Check connector polarity; external charging only|
|5 V regulator|Pololu 4082 S13V30F5|Lab power implementation, not PCB converter validation|
|3.3 V regulator|Pololu 4980 S13V25F3|Do not parallel with DevKit 3.3 V output|
|Analog LDO|TPS7A2030PDBVR on Adafruit 1230|Specified pad/header mapping and local soldered bypass|
|SD|Adafruit 4682|3.3 V interface; SDIO wiring in current tables|
|USB inlet|Adafruit 1833|External inlet, VBUS sense-only; both DevKit sockets unused|
|EMG|Bare MyoWare 2.0|VIN/GND/RAW pads; ENV/RECT unused|
|Breadboards|BusBoard BB830|63 rows; unused long power rails|
|ADC|RoboticsBD RBD-3184 / HW-AD7606-F4|Photo-labeled headers; serial configuration and VIO measured before connection|
|IMUs|Two RoboticsBD GY-521 / MPU-6050 modules|Photo-labeled header; regulator/pull-up qualification required|

The full physical terminal/hole plan is in build-guide.html. Body shapes and wire bends remain illustrative where manufacturer mechanical CAD is unavailable. Use printed pad labels and header orientation, not apparent model position. Local availability and delivered-board revision still need procurement checks; no order has been placed.

Read physical-assembly.md, module-qualification.md and bench-pcb-differences.md. They distinguish supplied module circuitry from final PCB power and controller layout. Rail noise, runtime and signal integrity remain physical tests.
