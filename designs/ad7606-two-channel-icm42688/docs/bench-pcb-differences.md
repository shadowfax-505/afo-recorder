# What the breadboard validates

The laboratory assembly and recorder PCB share ADC family, signal-conditioning transfer functions, logical interfaces and recording behavior. They are not physically identical power and controller implementations.

| Block | Laboratory implementation | Custom PCB / remaining test |
|---|---|---|
| Controller | ESP32-S3-DevKitC-1 N8R8 with onboard regulator/reset circuit | WROOM module, local reset/power/USB layout; repeat power-up and USB tests |
| Digital power | Selected Pololu regulator | TPS63070 and its PCB switching loop; bench success does not validate that loop |
| Analog rail | TPS7A2030 on soldered adapter with local capacitors | Same regulator on PCB; repeat ripple, stability and load checks |
| AD7606 5 V | Pololu 5 V regulator/module supply | TPS60150 charge pump; independently verify current capability, ripple and startup |
| Reverse polarity | Protected battery with verified source polarity | PCB reverse-polarity MOSFET; separately verify correct and reversed-input behavior with limited energy |
| Analog amplifiers | MCP6002 DIP packages | MCP6004/MCP6001 same family in SMD packages; layout, offsets, parasitics and noise differ |
| ADC | Qualified RBD-3184 AD7606 module | Bare AD7606 plus local reference/decoupling; verify power, filter and timing after assembly |
| SD command | GPIO47 avoids development-board LED loading | GPIO38; use the matching PCB firmware |
| USB | External inlet and short wired data pair, host VBUS sensed separately | Routed native USB-C interface; repeat enumeration and attachment interlock |
| Sensors | Selected remote ready-made IMU and bare MyoWare modules | Same external module identities; validate cable length and orientation |

No solderless breadboard test can certify final switching-loop, RF, thermal or USB layout performance. The current PCB is an engineering prototype. Ordering follows successful lab gates and a layout/assembly review; a subsequent PCB bring-up remains necessary. Do not build switching converters from loose ICs on a solderless breadboard to try to remove this distinction.
