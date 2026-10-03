# AD7606 fixed-two recorder with ICM-42688-P

This package uses the AD7606 path, exactly two MyoWare inputs, and two ICM-42688-P modules. Four-channel firmware is intentionally unsupported.

1. Read the [current integrated verification report](integrated-verification.html). Its incomplete cases and model limits are part of the build handoff.
2. Open [the assembly workspace](../viewer/build.html) and begin at Stage 1.
3. Read [selected lab parts](selected-lab-parts.md) and [module qualification](module-qualification.md) before wiring a module.
4. Follow [staged build guide](staged-build-guide.md) for measurements and gates.
5. Use the package IMU guidance at Stage 6 and [SD card wiring](sd-card-wiring.md) at Stage 7.
6. Read [validation report](validation-report.md) before interpreting any automated pass.

The whole-project manual is available at <https://shadowfax-505.github.io/afo-recorder/documentation/>. Hardware measurements remain pending.

## Breadboard handoff

[Applied simulation findings](breadboard-refinements.html) · [Probe contacts](../breadboard/probe-connections.csv) · [Blank bench checklist](bench-checklist.csv) · [Current breadboard lab kit](../breadboard/breadboard-lab-kit.zip). The ten interactive stages and wire instructions now describe the fixed-two AD7606/ICM build, current v1.6 firmware and separate SD/Wi-Fi quality checks. Physical results remain unmeasured.
