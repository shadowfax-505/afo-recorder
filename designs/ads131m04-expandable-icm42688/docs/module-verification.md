# Module connections and qualification

Physical terminal assignments are now specified below and in [the build guide](build-guide.html). Follow [module qualification](module-qualification.md) before energizing them. The terminal plan is complete; received-hardware configuration and measurements are not marked passed. Do not use old PENDING tables in archived reports.

|Module|Net|Physical terminal|Stage|
|---|---|---|---|
|adc|3V0A|TP2 / AVDD|3|
|adc|3V3D|TP1 / DVDD|3|
|adc|ADC_CS|J6.4 / CS|3|
|adc|ADC_DRDY|J6.6 / DRDY|3|
|adc|ADC_MISO|J6.7 / DOUT|3|
|adc|ADC_MOSI|J6.2 / DIN|3|
|adc|ADC_RESET|J6.1 / SYNC / RESET|3|
|adc|ADC_SCK|J6.5 / SCLK|3|
|adc|AIN0N|J1.3 / AIN0N|4|
|adc|AIN0P|J1.1 / AIN0P|4|
|adc|AIN1N|J2.3 / AIN1N|5|
|adc|AIN1P|J2.1 / AIN1P|5|
|adc|AIN2N|J3.3 / AIN2N|5|
|adc|AIN2P|J3.1 / AIN2P|5|
|adc|AIN3N|J4.3 / AIN3N|5|
|adc|AIN3P|J4.1 / AIN3P|5|
|adc|GND|J6.8 / GND|3|
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

The TI evaluation board requires [this adaptation](ads-evm-adaptation.md).
