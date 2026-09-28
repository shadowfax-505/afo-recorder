# Complete wire table

Project lead: Muttakin Rahman

Use the [guided build](../viewer/build.html). Ground connection for microSD is included. Follow module qualification before power-up.

|Wire|Stage|Net|From|To|
|---|---|---|---|---|
|wire-001|9|SOURCE_POS|battery:JST-PH red + lead|DIST1:a1|
|wire-002|1|SOURCE_POS|power-switch:SPST solder lug 1|DIST1:b1|
|wire-003|1|SOURCE_POS|lab-supply:Red + binding post|DIST1:c1|
|wire-004|1|GND|DIST1:a2|DIST1:a3|
|wire-005|1|GND|DIST1:b3|DIST1:a4|
|wire-006|1|GND|DIST1:b4|DIST1:a5|
|wire-007|1|GND|DIST1:b5|DIST1:a6|
|wire-008|1|GND|DIST1:b6|DIST1:a7|
|wire-009|1|GND|DIST1:b7|DIST1:a8|
|wire-010|1|GND|DIST1:b8|DIST1:a9|
|wire-011|1|GND|DIST1:b9|DIST1:a10|
|wire-012|1|GND|DIST1:b10|DIST1:a11|
|wire-013|1|GND|DIST1:b11|DIST1:a12|
|wire-014|1|GND|BB0:e6|DIST1:b2|
|wire-015|4|GND|BB1:d6|DIST1:c2|
|wire-016|5|GND|BB2:d6|DIST1:d2|
|wire-017|5|GND|BB3:d6|DIST1:e2|
|wire-018|5|GND|BB4:d6|DIST1:c3|
|wire-019|2|GND|AUX1:g23|DIST1:d3|
|wire-020|2|GND|AUX1:g31|DIST1:e3|
|wire-021|2|GND|AUX1:g39|DIST1:c4|
|wire-022|2|GND|AUX1:g47|DIST1:d4|
|wire-023|2|GND|AUX1:g51|DIST1:e4|
|wire-024|2|GND|AUX2:g3|DIST1:c5|
|wire-025|1|GND|lab-supply:Black COM binding post|DIST1:d5|
|wire-026|1|GND|reg3:GND / 5-pin row 3|DIST1:e5|
|wire-027|1|GND|reg5:GND / 5-pin row 3|DIST1:c6|
|wire-028|9|GND|battery:JST-PH black − lead|DIST1:d6|
|wire-029|2|GND|esp:J1.22 / GND|DIST1:e6|
|wire-030|1|GND|ldo:GND pin2 → JP2.2|DIST1:c7|
|wire-031|3|GND|adc:J6.8 / GND|DIST1:d7|
|wire-032|10|GND|myo1:GND solder pad|DIST1:e7|
|wire-033|4|GND|clamp1:CHIP_PAD_1 → JP1.2|DIST1:c8|
|wire-034|10|GND|myo2:GND solder pad|DIST1:d8|
|wire-035|5|GND|clamp2:CHIP_PAD_1 → JP1.2|DIST1:e8|
|wire-036|10|GND|myo3:GND solder pad|DIST1:c9|
|wire-037|5|GND|clamp3:CHIP_PAD_1 → JP1.2|DIST1:d9|
|wire-038|10|GND|myo4:GND solder pad|DIST1:e9|
|wire-039|5|GND|clamp4:CHIP_PAD_1 → JP1.2|DIST1:c10|
|wire-040|6|GND|foot:mikroBUS 8 / GND|DIST1:d10|
|wire-041|6|GND|shank:mikroBUS 8 / GND|DIST1:e10|
|wire-042|2|GND|button:NO contact 2|DIST1:c11|
|wire-043|2|GND|usb:JP2.1 / GND|DIST1:d11|
|wire-044|2|GND|usb-q:SOURCE pin2 → JP1.3|DIST1:e11|
|wire-045|6|GND|foot:mikroBUS 16 / SNC|DIST1:b12|
|wire-046|6|GND|foot:mikroBUS 9 / GND|DIST1:c12|
|wire-047|6|GND|shank:mikroBUS 16 / SNC|DIST1:d12|
|wire-048|6|GND|shank:mikroBUS 9 / GND|DIST1:e12|
|wire-049|2|VBAT|AUX1:a43|DIST1:a13|
|wire-050|1|VBAT|power-switch:SPST solder lug 2|DIST1:b13|
|wire-051|1|VBAT|reg5:VIN / 5-pin row 2|DIST1:c13|
|wire-052|1|VBAT|reg3:VIN / 5-pin row 2|DIST1:d13|
|wire-053|2|5V|reg5:VOUT / 5-pin row 5|esp:J1.21 / 5V|
|wire-054|1|3V3D|DIST1:a14|DIST1:a15|
|wire-055|1|3V3D|DIST1:b15|DIST1:a16|
|wire-056|1|3V3D|DIST1:b16|DIST1:a17|
|wire-057|3|3V3D|AUX1:a3|DIST1:b14|
|wire-058|6|3V3D|AUX1:a7|DIST1:c14|
|wire-059|6|3V3D|AUX1:a11|DIST1:d14|
|wire-060|2|3V3D|AUX1:a15|DIST1:e14|
|wire-061|2|3V3D|AUX2:a7|DIST1:c15|
|wire-062|1|3V3D|reg3:VOUT / 5-pin row 5|DIST1:d15|
|wire-063|1|3V3D|ldo:IN pin1 → JP2.1|DIST1:e15|
|wire-064|1|3V3D|ldo:EN pin3 → JP2.3|DIST1:c16|
|wire-065|3|3V3D|adc:TP1 / DVDD|DIST1:d16|
|wire-066|6|3V3D|foot:mikroBUS 7 / 3.3V|DIST1:e16|
|wire-067|6|3V3D|shank:mikroBUS 7 / 3.3V|DIST1:b17|
|wire-068|7|3V3D|sd:JP1.1 / 3V3|DIST1:c17|
|wire-069|1|3V0A|DIST1:a18|DIST1:a19|
|wire-070|1|3V0A|DIST1:b19|DIST1:a20|
|wire-071|1|3V0A|DIST1:b20|DIST1:a21|
|wire-072|1|3V0A|DIST1:b21|DIST1:a22|
|wire-073|1|3V0A|BB0:d2|DIST1:b18|
|wire-074|4|3V0A|BB1:h10|DIST1:c18|
|wire-075|5|3V0A|BB2:h10|DIST1:d18|
|wire-076|5|3V0A|BB3:h10|DIST1:e18|
|wire-077|5|3V0A|BB4:h10|DIST1:c19|
|wire-078|1|3V0A|ldo:OUT pin5 / 3.0V → JP1.1|DIST1:d19|
|wire-079|3|3V0A|adc:TP2 / AVDD|DIST1:e19|
|wire-080|10|3V0A|myo1:VIN solder pad|DIST1:c20|
|wire-081|4|3V0A|clamp1:CHIP_PAD_2 → JP1.3|DIST1:d20|
|wire-082|10|3V0A|myo2:VIN solder pad|DIST1:e20|
|wire-083|5|3V0A|clamp2:CHIP_PAD_2 → JP1.3|DIST1:c21|
|wire-084|10|3V0A|myo3:VIN solder pad|DIST1:d21|
|wire-085|5|3V0A|clamp3:CHIP_PAD_2 → JP1.3|DIST1:e21|
|wire-086|10|3V0A|myo4:VIN solder pad|DIST1:b22|
|wire-087|5|3V0A|clamp4:CHIP_PAD_2 → JP1.3|DIST1:c22|
|wire-088|3|ADC_CS|AUX1:g3|DIST1:a23|
|wire-089|3|ADC_CS|esp:J1.16 / GPIO10|DIST1:b23|
|wire-090|3|ADC_CS|adc:J6.4 / CS|DIST1:c23|
|wire-091|3|ADC_SCK|esp:J1.18 / GPIO12|adc:J6.5 / SCLK|
|wire-092|3|ADC_MISO|esp:J1.19 / GPIO13|adc:J6.7 / DOUT|
|wire-093|3|ADC_RESET|esp:J1.15 / GPIO9|adc:J6.1 / SYNC / RESET|
|wire-094|3|ADC_DRDY|esp:J1.12 / GPIO8|adc:J6.6 / DRDY|
|wire-095|3|ADC_MOSI|esp:J1.17 / GPIO11|adc:J6.2 / DIN|
|wire-096|4|AIN0P|BB1:c28|DIST1:a24|
|wire-097|4|AIN0P|adc:J1.1 / AIN0P|DIST1:b24|
|wire-098|4|AIN0N|BB1:c32|DIST1:a25|
|wire-099|4|AIN0N|adc:J1.3 / AIN0N|DIST1:b25|
|wire-100|10|RAW0|BB1:b2|DIST1:a26|
|wire-101|10|RAW0|myo1:RAW solder pad|DIST1:b26|
|wire-102|4|RC0A|BB1:d4|DIST1:a27|
|wire-103|4|RC0A|clamp1:CHIP_PAD_3 → JP2.3|DIST1:b27|
|wire-104|5|AIN1P|BB2:c28|DIST1:a28|
|wire-105|5|AIN1P|adc:J2.1 / AIN1P|DIST1:b28|
|wire-106|5|AIN1N|BB2:c32|DIST1:a29|
|wire-107|5|AIN1N|adc:J2.3 / AIN1N|DIST1:b29|
|wire-108|10|RAW1|BB2:b2|DIST1:a30|
|wire-109|10|RAW1|myo2:RAW solder pad|DIST1:b30|
|wire-110|5|RC1A|BB2:d4|DIST1:a31|
|wire-111|5|RC1A|clamp2:CHIP_PAD_3 → JP2.3|DIST1:b31|
|wire-112|5|AIN2P|BB3:c28|DIST1:a32|
|wire-113|5|AIN2P|adc:J3.1 / AIN2P|DIST1:b32|
|wire-114|5|AIN2N|BB3:c32|DIST1:a33|
|wire-115|5|AIN2N|adc:J3.3 / AIN2N|DIST1:b33|
|wire-116|10|RAW2|BB3:b2|DIST1:a34|
|wire-117|10|RAW2|myo3:RAW solder pad|DIST1:b34|
|wire-118|5|RC2A|BB3:d4|DIST1:a35|
|wire-119|5|RC2A|clamp3:CHIP_PAD_3 → JP2.3|DIST1:b35|
|wire-120|5|AIN3P|BB4:c28|DIST1:a36|
|wire-121|5|AIN3P|adc:J4.1 / AIN3P|DIST1:b36|
|wire-122|5|AIN3N|BB4:c32|DIST1:a37|
|wire-123|5|AIN3N|adc:J4.3 / AIN3N|DIST1:b37|
|wire-124|10|RAW3|BB4:b2|DIST1:a38|
|wire-125|10|RAW3|myo4:RAW solder pad|DIST1:b38|
|wire-126|5|RC3A|BB4:d4|DIST1:a39|
|wire-127|5|RC3A|clamp4:CHIP_PAD_3 → JP2.3|DIST1:b39|
|wire-128|6|IMU_MOSI|esp:J1.4 / GPIO4|DIST1:a40|
|wire-129|6|IMU_MOSI|foot:mikroBUS 6 / MOSI|DIST1:b40|
|wire-130|6|IMU_MOSI|shank:mikroBUS 6 / MOSI|DIST1:c40|
|wire-131|6|IMU_MISO|esp:J1.5 / GPIO5|DIST1:a41|
|wire-132|6|IMU_MISO|foot:mikroBUS 5 / MISO|DIST1:b41|
|wire-133|6|IMU_MISO|shank:mikroBUS 5 / MISO|DIST1:c41|
|wire-134|6|IMU_SCK|esp:J1.6 / GPIO6|DIST1:a42|
|wire-135|6|IMU_SCK|foot:mikroBUS 4 / SCK|DIST1:b42|
|wire-136|6|IMU_SCK|shank:mikroBUS 4 / SCK|DIST1:c42|
|wire-137|6|FOOT_CS|AUX1:g7|DIST1:a43|
|wire-138|6|FOOT_CS|esp:J1.7 / GPIO7|DIST1:b43|
|wire-139|6|FOOT_CS|foot:mikroBUS 3 / CS|DIST1:c43|
|wire-140|6|FOOT_INT|esp:J1.9 / GPIO16|foot:mikroBUS 15 / INT|
|wire-141|6|SHANK_CS|AUX1:g11|DIST1:a44|
|wire-142|6|SHANK_CS|esp:J1.8 / GPIO15|DIST1:b44|
|wire-143|6|SHANK_CS|shank:mikroBUS 3 / CS|DIST1:c44|
|wire-144|6|SHANK_INT|esp:J1.10 / GPIO17|shank:mikroBUS 15 / INT|
|wire-145|2|BUTTON|AUX1:g15|DIST1:a45|
|wire-146|2|BUTTON|esp:J1.11 / GPIO18|DIST1:b45|
|wire-147|2|BUTTON|button:NO contact 1|DIST1:c45|
|wire-148|2|LED_REC|AUX1:a19|DIST1:a46|
|wire-149|2|LED_REC|esp:J3.7 / GPIO41|DIST1:b46|
|wire-150|2|LED_REC_A|AUX1:g19|DIST1:a47|
|wire-151|2|LED_REC_A|AUX1:a23|DIST1:b47|
|wire-152|2|LED_ERR|AUX1:a27|DIST1:a48|
|wire-153|2|LED_ERR|esp:J3.6 / GPIO42|DIST1:b48|
|wire-154|2|LED_ERR_A|AUX1:g27|DIST1:a49|
|wire-155|2|LED_ERR_A|AUX1:a31|DIST1:b49|
|wire-156|2|LED_LOW|AUX1:a35|DIST1:a50|
|wire-157|2|LED_LOW|esp:J3.5 / GPIO2|DIST1:b50|
|wire-158|2|LED_LOW_A|AUX1:g35|DIST1:a51|
|wire-159|2|LED_LOW_A|AUX1:a39|DIST1:b51|
|wire-160|2|BAT_SENSE|AUX1:g43|DIST1:a52|
|wire-161|2|BAT_SENSE|AUX1:a47|DIST1:b52|
|wire-162|2|BAT_SENSE|AUX1:a51|DIST1:c52|
|wire-163|2|BAT_SENSE|esp:J3.4 / GPIO1|DIST1:d52|
|wire-164|2|USB_VBUS|AUX1:a55|DIST1:a53|
|wire-165|2|USB_VBUS|usb:JP2.5 / VBUS|DIST1:b53|
|wire-166|2|USB_GATE|AUX1:g55|DIST1:a54|
|wire-167|2|USB_GATE|AUX2:a3|DIST1:b54|
|wire-168|2|USB_GATE|usb-q:GATE pin1 → JP1.2|DIST1:c54|
|wire-169|2|USB_PRESENT_N|AUX2:g7|DIST1:a55|
|wire-170|2|USB_PRESENT_N|usb-q:DRAIN pin3 → JP2.3|DIST1:b55|
|wire-171|2|USB_PRESENT_N|esp:J3.18 / GPIO21|DIST1:c55|
|wire-172|2|USB_DM|usb:JP2.4 / D-|usb-dm-r:lead 1|
|wire-173|2|USB_DM_MCU|usb-dm-r:lead 2|esp:J3.20 / GPIO19|
|wire-174|2|USB_DP|usb:JP2.3 / D+|usb-dp-r:lead 1|
|wire-175|2|USB_DP_MCU|usb-dp-r:lead 2|esp:J3.19 / GPIO20|
|wire-176|7|SD_CMD|esp:J3.17 / GPIO47|sd:JP1.5|
|wire-177|7|SD_CLK|esp:J3.9 / GPIO39|sd:JP1.3|
|wire-178|7|SD_D0|esp:J3.8 / GPIO40|sd:JP1.4|
|wire-179|1|3V3D|cap-2:lead 1|ldo:U$1.1 solder pad|
|wire-180|1|GND|cap-2:lead 2|ldo:U$1.2 solder pad|
|wire-181|1|3V0A|cap-3:lead 1|ldo:U$1.6 solder pad|
|wire-182|1|GND|cap-3:lead 2|ldo:U$1.2 solder pad|
|wire-183|7|GND|sd:JP1.2 / GND|BB0:d24|
