# Project status

## Integrated refinement — 1 October 2026

The [fixed two-channel AD7606 / ICM build](../designs/ad7606-two-channel-icm42688/docs/integrated-verification.html) now exercises acquisition, real FreeRTOS/FatFS and UDP together. Simulation exposed and helped correct ADC servicing delays and IMU timestamp regressions. Ten complete cloud cases pass; nominal file/data checks also pass, with a failed optional trace download. Four cases remain quota-blocked and the battery evidence export is partial. The full matrix remains open. All seven lab profiles recompiled as the v1.6 source set, adding required BUSY assertion before an ADC reading is accepted. Sixteen ADC groups and a 60-second native driver pipeline pass, while all eighteen current-image cloud cases remain pending. Earlier diagnostic and lifecycle evidence is archived with its tested source/image identity. Physical power/noise/timing/storage/radio/runtime tests remain pending. Other five packages are unchanged. The sections below describe the earlier six-package release.

## Completed

The six-setups implementation is complete as editable engineering deliverables: three original ICM variants plus three independent MPU alternatives. The MPU firmware, data tools, CAD checks, exports, examples and viewers are verified at software/design level. Original ICM source packages are preserved.

Project organization and first documentation set are complete in this folder. Descriptive package names and document names are used. Standard source/build/CAD filenames are retained to preserve tool behavior. Manufacturer attribution and truthful test status remain in place. Python caches and workstation-specific text paths are excluded from the organized release.

## Remaining verification

Complete the pending cloud matrix and current-image diagnostic/lifecycle reruns when Wokwi execution becomes available. Keep these results separate from the physical gates below.

1. Obtain exact module header schematics or clear photos and continuity measurements.
2. Verify the new GPIO47 SD command connection and run the stage-7 storage tests with the matching breadboard build.
3. Perform the staged lab tests and enter measured results.
4. Review the final PCB for ordering after successful bench tests.

New faults or changed firmware require fresh checks. Synthetic passes do not establish physical measurements. No hardware order is pending.

## Wokwi runner follow-up

Fifteen historical sensor-runner regression tests and sixteen integrated-runner tests reject false-positive evidence. Sixteen native C groups check the current ADC driver and eight check the IMU clock helper. Seven earlier Wokwi diagnostic cases remain available with their tested image; current-image reruns are pending. Credentials are configured locally and are not part of any package.
