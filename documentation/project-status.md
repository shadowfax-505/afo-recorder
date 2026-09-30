# Project status

## Focused refinement — 30 September 2026

The [fixed two-channel AD7606 / ICM build](../designs/ad7606-two-channel-icm42688/docs/circuit-audit.html) now has corrected diagnostics/metadata, fresh circuit checks, expanded analog simulations and a shorter lab guide. Wokwi system execution remains unresolved; it is not a passed hardware or complete virtual-validation gate. Other five packages are unchanged. The sections below describe the earlier six-package release.

## Completed

The six-setups implementation is complete as editable engineering deliverables: three original ICM variants plus three independent MPU alternatives. The MPU firmware, data tools, CAD checks, exports, examples and viewers are verified at software/design level. Original ICM source packages are preserved.

Project organization and first documentation set are complete in this folder. Descriptive package names and document names are used. Standard source/build/CAD filenames are retained to preserve tool behavior. Manufacturer attribution and truthful test status remain in place. Python caches and workstation-specific text paths are excluded from the organized release.

## Next work requires hardware evidence

1. Obtain exact module header schematics or clear photos and continuity measurements.
2. Verify the new GPIO47 SD command connection and run the stage-7 storage tests with the matching breadboard build.
3. Perform the staged lab tests and enter measured results.
4. Review the final PCB for ordering after successful bench tests.

Do not repeat completed software work or imply physical measurements from synthetic tests. No hardware order is pending. Continuation automation can stop after final organized-release checks pass; further changes should follow new user input or lab evidence.

## Wokwi runner follow-up

Fourteen synthetic regression tests now protect against false-positive simulation results, including stale output files, wrong channel extrema, incorrect sample rates and header-only traces. Wokwi ESP32 acquisition remains unverified because of the unresolved SPI contention. The runner needs a locally configured `WOKWI_CLI_TOKEN` for automated execution; no token belongs in this repository.
