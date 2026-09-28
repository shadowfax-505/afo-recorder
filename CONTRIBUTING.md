# Contributing

Contributions are welcome when they preserve the recorder's configuration boundaries and evidence trail.

## Before changing a design

1. Identify the exact package: ADC, supported EMG count, and IMU family.
2. State whether the change affects the breadboard, compact PCB, firmware, recording format, converter, or viewer.
3. Keep breadboard and PCB differences explicit, especially SD GPIOs, module regulators, and carrier-board loading.
4. Update the affected pin map, metadata, test fixture, and documentation together.

## Evidence expectations

- Label generated inputs and simulations as synthetic.
- Keep measured results separate from automated checks.
- Include the hardware revision, firmware manifest or hash, instruments, settings, raw readings, acceptance limit, and evidence filename for a bench result.
- Do not mark a physical gate passed without the associated measurement record.
- Preserve manufacturer attribution, source URLs, and applicable licence text.

## Useful checks

Run the package's host test suite after changing the format, converter, or live receiver. Run KiCad ERC and DRC after changing a schematic or board. Run `documentation/validate_physical_wiring.py` after changing a breadboard plan or connection table. Exercise the corresponding build, assembly, and PCB pages after changing a viewer.

Human testing, electrical-safety decisions, and manufacturing approval require review outside the software contribution process.
