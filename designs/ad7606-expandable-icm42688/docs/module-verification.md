# Module connections and qualification

Physical terminal assignments are now specified below and in [the build guide](build-guide.html). Follow [module qualification](module-qualification.md) before energizing them. The terminal plan is complete; received-hardware configuration and measurements are not marked passed. Do not use old PENDING tables in archived reports.

|Module|Net|Physical terminal|Stage|
|---|---|---|---|
|adc|3V3D|VIO / CN1 photo label|3|
|adc|5V|+5V / CN1 photo label|3|
|adc|ADC_CONVST|CVA / CN1 photo label|3|
|adc|ADC_CONVST|CVB / CN1 photo label|3|
|adc|ADC_CS|CS / CN1 photo label|3|
|adc|ADC_DRDY|BUSY / CN1 photo label|3|
|adc|ADC_MISO|DB7 / CN1 photo label|3|
|adc|ADC_RESET|RST / CN1 photo label|3|
|adc|ADC_SCK|RD / CN1 photo label|3|
|adc|AIN0P|V1 / CN2 photo label|4|
|adc|AIN1P|V2 / CN2 photo label|5|
|adc|AIN2P|V3 / CN2 photo label|5|
|adc|AIN3P|V4 / CN2 photo label|5|
|adc|GND|DB0 / CN1 photo label|3|
|adc|GND|DB1 / CN1 photo label|3|
|adc|GND|DB10 / CN1 photo label|3|
|adc|GND|DB11 / CN1 photo label|3|
|adc|GND|DB12 / CN1 photo label|3|
|adc|GND|DB13 / CN1 photo label|3|
|adc|GND|DB14 / CN1 photo label|3|
|adc|GND|DB15 / CN1 photo label|3|
|adc|GND|DB2 / CN1 photo label|3|
|adc|GND|DB3 / CN1 photo label|3|
|adc|GND|DB4 / CN1 photo label|3|
|adc|GND|DB5 / CN1 photo label|3|
|adc|GND|DB6 / CN1 photo label|3|
|adc|GND|DB9 / CN1 photo label|3|
|adc|GND|G beside V1 / CN2 photo label|3|
|adc|GND|G beside V2 / CN2 photo label|3|
|adc|GND|G beside V3 / CN2 photo label|3|
|adc|GND|G beside V4 / CN2 photo label|3|
|adc|GND|GND / CN1 photo label|3|
|adc|GND|OS0 / CN1 photo label|3|
|adc|GND|OS1 / CN1 photo label|3|
|adc|GND|OS2 / CN1 photo label|3|
|adc|GND|RAGE / CN1 photo label|3|
|adc|GND|V5 unused input / CN2 photo label|3|
|adc|GND|V6 unused input / CN2 photo label|3|
|adc|GND|V7 unused input / CN2 photo label|3|
|adc|GND|V8 unused input / CN2 photo label|3|
|foot|3V3D|mikroBUS 7 / 3.3V|6|
|foot|FOOT_CS|mikroBUS 3 / CS|6|
|foot|FOOT_INT|mikroBUS 15 / INT|6|
|foot|GND|mikroBUS 16 / SNC|6|
|foot|GND|mikroBUS 8 / GND|6|
|foot|GND|mikroBUS 9 / GND|6|
|foot|IMU_MISO|mikroBUS 5 / MISO|6|
|foot|IMU_MOSI|mikroBUS 6 / MOSI|6|
|foot|IMU_SCK|mikroBUS 4 / SCK|6|
|shank|3V3D|mikroBUS 7 / 3.3V|6|
|shank|GND|mikroBUS 16 / SNC|6|
|shank|GND|mikroBUS 8 / GND|6|
|shank|GND|mikroBUS 9 / GND|6|
|shank|IMU_MISO|mikroBUS 5 / MISO|6|
|shank|IMU_MOSI|mikroBUS 6 / MOSI|6|
|shank|IMU_SCK|mikroBUS 4 / SCK|6|
|shank|SHANK_CS|mikroBUS 3 / CS|6|
|shank|SHANK_INT|mikroBUS 15 / INT|6|

AD7606 PAR/SER, STBY and REFSELECT are onboard configuration checks, not extra unknown header wires.
