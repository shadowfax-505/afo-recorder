# Project status

## Integrated refinement — 1 October 2026

The [fixed two-channel AD7606 / ICM build](../designs/ad7606-two-channel-icm42688/docs/integrated-verification.html) passes all 18 v1.6 integrated cases in Wokwi’s web editor. Current file and laptop socket/API/browser/archive checks pass with documented substitutes; wireless losses stay visible and saved nominal acquisition remains complete. All seven laboratory profiles compile; they now use source set 1.8 (32/30 µs ICM-42688 timestamp ticks, 2.44 s PSRAM record queue, per-device Wi-Fi password, IMU timestamp-scale checks), which has not been rerun in Wokwi. QEMU adds refusal evidence but fails nominal timing qualification. Historical diagnostic/lifecycle images and incomplete CLI outcomes remain preserved. No physical recorder has been measured. Other five packages are unchanged. The sections below describe the earlier six-package release.

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
