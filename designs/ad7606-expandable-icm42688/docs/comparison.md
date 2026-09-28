# Two recorder versions

Both use an ESP32-S3-N8R8 controller, four populated analog inputs, two or four enabled channels at8 kHz, ready-made foot/shank ICM-42688-P modules at200 Hz, SD recording and best-effort Wi-Fi. Each package has one75×50 mm four-layer PCB. They are alternatives, not pin-compatible ADC substitutions.

| Choice | ADS131M04 | AD7606 |
|---|---|---|
| Lab module | Exact evaluation/breakout board not selected; availability dependent | RoboticsBD RBD-3184, photo marked HW-AD7606-F4; physical header mapping pending |
| Result | Signed24-bit simultaneous frames | Signed16-bit simultaneous conversions; all8 words read |
| Analog mapping | Two RC stages, gain0.5 around1.5 V midpoint; differential ADC input | Two unity-gain RC stages; ground-referenced ADC input |
| Nominal ADC full scale | ±1.2 V at PGA1 | ±5 V selected |
| Ideal voltage/code | 0.1431 µV at ADC, before input scaling | 152.588 µV at ADC |
| Interpretation | Word width is not measured effective resolution | 0–3 V spans about19661 codes; not an ENOB claim |
| ADC supply/clock | 3.0 V analog /3.3 V digital;8.192 MHz external clock | 5 V analog /3.3 V interface; CONVST at8 kHz, internal conversion timing |
| Timing retained | Host DRDY timestamp; sinc-filter latency must be characterized | Software timestamp immediately before CONVST; BUSY completion and read timing retained |
| Integrity | ADC-frame CRC plus file/packet checks | No chip-frame CRC; file/packet checks and timing faults only |
| Configuration | Disable unused ADC channels in2ch mode | All8 ADC channels convert; only enabled2/4 EMG channels exported, V5–V8 grounded |
| Procurement gate | Obtain exact board schematic and verify clock/input loading | Verify header, serial straps, DOUTA and VIO on actual module |

**Shared does not mean physically identical.** Breadboard DIP buffers use the same amplifier family but different packages. Development-board power and USB circuits differ. Lab rails can substitute temporarily for final regulators, but do not validate switching loops, reverse-battery protection or radio current transients. Record all fixture differences and repeat those tests on the final board.

Sources: [TI ADS131M04](https://www.ti.com/lit/ds/symlink/ads131m04.pdf), [ADI AD7606](https://www.analog.com/media/en/technical-documentation/data-sheets/ad7606_7606-6_7606-4.pdf), [TI TPS60150](https://www.ti.com/lit/ds/symlink/tps60150.pdf), [Espressif module](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf). These describe ICs; they do not verify a seller module's wiring.

No physical test has been completed. Simulated plots and generated example recordings are labeled synthetic. Manufacturing exports remain engineering prototypes, with ordering gated by lab results and final design/assembly review.
