# Current validation status — 30 September 2026

Read the [focused circuit audit](circuit-audit.md) and [short staged guide](lab-quickstart.md). Fresh ERC/DRC and 390 direct pin comparisons pass, as do 40 host tests and seven software acquisition scenarios. Seven firmware profiles were rebuilt. Analog response, tolerance and DC/loading simulations pass under the documented surrogate models. **Seven actual-firmware Wokwi scenarios now pass serial and VCD protocol checks. The specified virtual gate passes within model/capture limits; physical testing has not been performed.** See the [execution report](virtual-verification.md).

The history below describes the earlier review, not the current firmware/build status.

---

# Validation history — 28 September 2026

Fresh checks: schematic-to-PCB parity and all-severity DRC (including excluded findings) pass; KiCad ERC and DRC completed with zero reported violations and zero unconnected items; freshly exported schematic connections match the circuit specification. Host regression tests pass. Detailed commands/results are in completion-checks/. These tests do not prove component ratings, manufacturing suitability or physical performance.

Breadboard checking additionally verifies unique insertion holes, no conflicting named nets, connected named nets including the adapter's known internal copper, single-contact wiring and GPIO labels. Stage dependencies now defer module wires until their module is installed. Viewer interactions were checked separately.

Physical terminal maps are specified. Remaining qualification is received-board inspection and measurement, not a request for another user design choice. Perform module-qualification.md and staged-build-guide.md. No hardware has been flashed or measured here. No human-use or manufacturing release is claimed. See bench-pcb-differences.md.

Firmware source/binaries and manufacturing geometry are unchanged in this review; previous successful build records remain in their manifests/logs. Fresh ERC/DRC is included, but cross-compilation was not repeated without a firmware change.

## Assembly review correction

Added the missing SD module ground lead at JP1.2 in the breadboard plan. The independent check now requires all five SDIO contacts and supply/ground presence for core modules. Prior net-short/occupancy checks could not detect an entirely omitted terminal. Current wiring checks pass; physical SD operation remains untested. PCB circuitry and firmware are unchanged by this correction.

## Follow-up: verification safeguards and driver logic

Fifteen synthetic runner regression tests now reject stale files, partial windows, wrong sample rates/channel values and empty traces. Ten native C test groups also execute the production AD7606 driver against mocked timer, BUSY and SPI APIs, including late-read and unread-conversion faults. These are separate from the 40 host/converter tests. They do not emulate ESP32 concurrency or measure physical timing. See `simulations/driver-tests/` and `simulations/wokwi/tests/`. Seven Wokwi execution scenarios pass; physical acceptance remains pending.
