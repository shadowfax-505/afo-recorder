# TI ADS131M04EVM adaptation

Selected lab carrier: TI ADS131M04EVM corresponding to SBAU332A/DC044 Rev A. Availability remains a procurement dependency. Use the [TI EVM manual](https://www.ti.com/lit/ug/sbau332a/sbau332a.pdf), especially Tables 2/6 and the schematic, to confirm the received revision before rework. This is an adaptation of a ready-made board, not an instruction to wire the bare ADC on a solderless breadboard.

With all power disconnected, remove/disconnect the PHI host board. Remove R45 and all JP9 shunts to isolate the host digital supply and onboard analog regulator. Feed TP1/DVDD with regulated 3.3 V and TP2/AVDD with regulated 3.0 V; connect J6.8 ground. Confirm isolation and no shorts with a meter before applying power. Never attach PHI or its USB at the same time.

Leave JP5 open to enable the onboard oscillator. Fit JP6 pins 1–2 for the onboard 8.192 MHz source. No external clock wire is needed; J6.3 is a monitor point, not a second clock input.

J6 assignments: 1 SYNC/RESET to GPIO9; 2 DIN to GPIO11; 3 clock monitor unconnected; 4 CS to GPIO10; 5 SCLK to GPIO12; 6 DRDY to GPIO8; 7 DOUT to GPIO13; 8 GND. J1–J4 correspond to channels 0–3: pin 1 AINP, pin 2 ground, pin 3 AINN. Use the board's pin-1 mark, not the illustrative model orientation.

To retain the recorder's external conditioning network, qualified solder rework is required: remove JP1–JP4 shunts and R1–R8 input shunts; replace R9–R16 (49.9 Ω) with 0 Ω links; remove differential capacitors C9–C12 (1 nF), since the external circuit already supplies its filter. Leave DNP R17–R24 and C1–C8 unpopulated. Preserve all converter decoupling, VCAP and oscillator circuitry. Inspect under magnification, check continuity from each input connector to the converter path, and record the rework in the results sheet.

If the board revision/component designators differ, reconcile its schematic first. Do not apply this rework by visual similarity. The longer lab wiring and EVM parasitics differ from the custom PCB, so successful DC and frequency-response tests do not establish final PCB noise or radio performance.
