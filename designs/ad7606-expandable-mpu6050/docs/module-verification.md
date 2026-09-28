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
|foot|3V3D|VCC / photo position 8|6|
|foot|FOOT_AD0|AD0 / photo position 2|6|
|foot|FOOT_INT|INT / photo position 1|6|
|foot|GND|GND / photo position 7|6|
|foot|IMU_SCL|SCL / photo position 6|6|
|foot|IMU_SDA|SDA / photo position 5|6|
|shank|3V3D|VCC / photo position 8|6|
|shank|GND|GND / photo position 7|6|
|shank|IMU_SCL|SCL / photo position 6|6|
|shank|IMU_SDA|SDA / photo position 5|6|
|shank|SHANK_AD0|AD0 / photo position 2|6|
|shank|SHANK_INT|INT / photo position 1|6|

AD7606 PAR/SER, STBY and REFSELECT are onboard configuration checks, not extra unknown header wires.
