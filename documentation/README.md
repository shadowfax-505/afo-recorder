# Project manual

This manual is the recommended reading path for the AFO Research Recorder. The [live documentation](https://shadowfax-505.github.io/afo-recorder/documentation/) presents the same project-level guidance in a web layout.

## Read in this order

1. **[Start here](start-here.md)** — choose one of the six configurations and understand the project boundaries.
2. **[System architecture](system-architecture.md)** — see how EMG, IMUs, storage, and Wi-Fi fit together.
3. **[Lab build guide](lab-build-guide.md)** — assemble and test the system through ten gates.
4. **[Firmware build guide](firmware-build-guide.md)** — select the correct hardware and diagnostic profile.
5. **[Recording and analysis](recording-and-analysis.md)** — record, convert, recover, and inspect data.
6. **[Validation status](validation-status.md)** — distinguish completed software checks from open hardware tests.

## Reference documents

| Question | Document |
|---|---|
| Which SD pins apply to the DevKit and PCB? | [SD card wiring](sd-card-wiring.md) |
| Are all named wires represented? | [Wiring coverage](wiring-status.md) |
| Which source supports a component or interface? | [Manufacturer evidence](manufacturer-evidence.md) |
| Is the design ready to build? | [Implementation readiness](implementation-readiness.md) |
| What changed in the public interface? | [Interface review](interface-review.md) |
| How was this documentation checked? | [Documentation review](documentation-review.md) |
| What was published and under whose authority? | [Publication record](publication.md) |
| What is the current project state? | [Project status](project-status.md) |

Each configuration also has a `docs/` folder. Package-specific documents override project-level summaries for component values, pin assignments, build commands, and acceptance thresholds.

## Evidence files

JSON and log files in this directory are machine-readable evidence, not prose documentation. Useful entry points include:

- `fresh-checks-20260928.json` — per-design ERC, DRC, specification, and host-test results.
- `release-checks.json` — release-wide navigation, test, and firmware-profile summary.
- `physical-wiring-validation.json` — named-net, hole, connector-contact, and GPIO checks.
- `recording-metadata-checks.json` — metadata checks across recording configurations.

Every one of these evidence files marks or implies that physical hardware measurements remain pending. Do not convert a software pass into a bench-test pass.
