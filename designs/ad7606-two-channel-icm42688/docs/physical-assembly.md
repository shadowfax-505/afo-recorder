# Physical assembly — revision 12

This is a defined terminal and breadboard-hole plan, not a physically validated recorder. Use the printable `build-guide.html` alongside the viewer. Module body positions and wire bends are illustrative; use printed connector labels, not apparent geometry, to identify terminals. Do not use rendered wire lengths as cut lengths.

## Assembly rules

Use BusBoard BB830 breadboards, 63 rows. Within a row, a–e are connected and f–j are connected; the center gap separates them. Verify this with a meter. The long power rails are unused. BB0 is midpoint, BB1 onward are analog channels; AUX boards hold controls and resistors; DIST boards distribute named nets. Install exactly one lead in each listed hole. Five-hole strips, not stacked jumper sockets, provide fanout.

Populate only the components and wires for the current stage. The hole tables list component pin numbers and orientation. Bend axial passive leads to the specified holes; insulate exposed leads where needed. LED anode/cathode and IC pin-1 orientation are mandatory. Solder SMD parts to their specified adapters; do not insert bare SMD parts into a breadboard. The existing analog circuit values remain unchanged.

The power switch is a two-terminal SPST switch, rated at least 1 A DC at 5 V, with solder lugs. The recording button is a two-terminal normally-open momentary contact. Verify their open/closed contact behavior before wiring. Do not substitute an illuminated switch with unidentified extra terminals.

Use one removable source lead: lab supply OR protected battery. Remove both lab supply leads before connecting the battery at stage 9. These are alternatives, not a power-sharing circuit. Set the lab supply initially to 3.7 V with a conservative current limit; raise the limit only after checking expected load and absence of shorts. A rail that collapses under current limiting is a failed test, not permission to increase current blindly.

LDO input/output 1 µF capacitors are local soldered components at the adapter's IC pads, not distribution-board components. Keep their leads a few millimeters long. Their shared ground is an intentional solder junction. Connect all grounds as listed. Keep converter loops and module decoupling local. Keep SPI wiring short with nearby ground return; begin on the bench with ≤10 cm signal leads and verify clock/data integrity. The exploded viewer spacing is not a recommended cable length.

## USB and programming

Use the selected Adafruit 1833 micro-B inlet: JP2.1 ground, JP2.3 D+, JP2.4 D−, JP2.5 VBUS sense; JP2.2 ID is unconnected. D+ and D− each pass through their own 33 Ω inline resistor close to ESP32 GPIO20 and GPIO19 respectively. Keep the data pair short and together, soldered rather than routed through breadboard strips. Both DevKit onboard USB sockets stay empty. The DevKit receives its listed external regulated 5 V supply. External USB VBUS feeds only the USB detection network, never the recorder's 5 V rail. Check enumeration and recording inhibition before relying on this lab programming arrangement. It is not a validated USB layout.

Unpowered: verify no direct VBUS-to-recorder-5V connection. Powered with host absent: verify no supply is driven onto inlet VBUS. With host present: verify USB detection is active and recording refuses to start. Do not bypass this gate. Bench instruments and USB are used only with synthetic signals and no person attached.

## Build sequence and result sheet

1. Rails and dummy loads: target 5.00 V ±5%, 3.30 V ±5%, 3.00 V ±3%; verify polarity before adding modules. Record startup and ripple waveforms; these screening limits do not replace component-specific limits or final noise validation.
2. Controller: programming/reset, buttons, LEDs, USB enumeration and recording inhibition.
3. Qualified AD7606: known DC levels and swapped V1/V2 identity test; both CVA/CVB share GPIO11. Check 8 kHz conversion cadence, BUSY assertion/deassertion and full 128-clock read through DB7/DOUTA. Separate discarded RESET-time reads from counted conversions; AD7606 has no sensor-frame CRC.
4. First analog channel: synthetic offset/amplitude sweep, clipping and filter response against simulation.
5. Second EMG channel: populate BB2 and verify exactly EMG1/2, common frame timestamps, crosstalk and the defined unused ADC levels. No EMG3/EMG4 ports exist in this fixed-two build.
6. First then second IMU: identity, orientation, 200 Hz nominal acquisition, FIFO and timing diagnostics.
7. SD: uninterrupted 60-minute synthetic recording, conversion, full-card and interrupted-file tests.
8. Wi-Fi with SD: visible wireless gaps and no unexplained SD sample loss.
9. Battery: disconnect lab supply; repeat startup and measure at least two hours runtime.
10. Bare MyoWare RAW integration; wearable/human work only after institutional review, informed consent and electrical-safety assessment. Disconnect chargers, USB and mains-connected test instruments while electrodes are attached.

For every stage record: date, hardware/module revision, firmware profile, instrument, stimulus/load, measured minimum/maximum, trace/file location, pass/fail, fault and corrective action. Earlier diagnostic stages remain available. Do not mark any measured row passed from a simulation.

Use [applied simulation findings](breadboard-refinements.html), [probe contacts](../breadboard/probe-connections.csv) and [blank bench checklist](bench-checklist.csv). See module-qualification.md before stage 3 or 6, the existing detailed staged-test guide for signal limits, and the per-wire and component tables below. If an older drawing disagrees, revision-12 tables supersede its breadboard routing; stop and reconcile any electrical discrepancy before power-up. PCB files are unchanged by this breadboard update; final layout-dependent validation remains required.
