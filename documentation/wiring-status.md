# Wiring coverage

All six viewers now show individual named-terminal connections for every subsystem and auxiliary control circuit. Each package includes `breadboard/system-wiring.json`, `breadboard/system-wiring.csv` and `docs/system-wiring.md`.

This closes the visual/electrical connection inventory, but it does not release unknown physical module pin maps. Amber virtual terminals must not be used as header coordinates. AD7606 headers, selected IMU/ADC carriers, USB VBUS access and auxiliary component hole allocation still require verification. Firmware and PCB outputs are unchanged.

## Photo update

Supplied AD7606 underside/component-side and GY-521 component-side images now establish label order for the matching pictured modules. Five affected viewers route those endpoints to photo-ordered headers. The AD7606 serial-mode data-pin grounds were completed. Mode selection, VIO isolation, regulator/pull-up paths and received-board continuity remain unverified. See each affected package’s docs/photo-pinmaps.md.
