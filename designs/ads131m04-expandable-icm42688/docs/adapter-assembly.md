# Soldered adapter assembly

Use one Adafruit 1230 carrier per device. Source: [manufacturer Eagle PCB](https://github.com/adafruit/Adafruit-SMT-Breakout-PCBs/blob/master/6-pin%20SOT-23.brd). The local source copy is `pinmap-evidence/adapter.brd`.

All header positions below use the **top U$1 component-side view**, with JP2 on the left and JP1 on the right. JP2.1 and JP1.1 are the upper pair; pin 2 is the middle pair; pin 3 is the lower pair. Header rows are 7.62 mm apart and pins are 2.54 mm apart. A bottom-side device must be soldered using the bottom Q1 footprint orientation, not this top-view outline.

| Device pad | Carrier header | Function |
|---|---|---|
| TPS7A2030 chip 1 → U$1.1 | JP2.1 | IN, 3.3 V |
| TPS7A2030 chip 2 → U$1.2 | JP2.2 | GND |
| TPS7A2030 chip 3 → U$1.3 | JP2.3 | EN, tie IN |
| TPS7A2030 chip 4 → U$1.4 | JP1.3 | NC, leave open |
| TPS7A2030 chip 5 → U$1.6 | JP1.1 | OUT, 3.0 V |
| U$1.5, no chip lead | JP1.2 | Leave open |
| Q1 chip 1 | JP1.2 | BAV199 GND / 2N7002 gate |
| Q1 chip 2 | JP1.3 | BAV199 3.0 V / 2N7002 source |
| Q1 chip 3 | JP2.3 | BAV199 signal / 2N7002 drain |

Populate only U$1 for the regulator, or only Q1 for each diode/transistor carrier. Never populate both sides. The regulator's fifth chip lead lands on **carrier pad 6**, not carrier pad 5. Confirm its five-lead footprint alignment before soldering. Fit the specified 1 uF input/output capacitors locally with short ground connections; do not substitute long remote breadboard leads for local bypassing.

Before powering, measure chip-to-header continuity for every populated lead, inspect bridges, and check no supply-to-ground short. CAD mapping is complete; solder quality and electrical performance are not measured. Multiple wires shown at the same header require a distribution junction; do not force multiple jumper sockets onto one pin. The remaining distribution/fixture implementation is tracked in the project implementation audit.
