# Continuous native driver check

The 60-second logical capture passes with 480,000 EMG records, 12,009 foot records and 12,001 shank records. Each exported EMG code matches the repeated ngspice-derived sample table. The real converter checks every record CRC, the finalized END counts, channel scaling, sequence continuity and timestamp monotonicity. All three streams have zero detected sequence gaps or timestamp regressions.

The independent modeled IMU clocks use 5,000.35 µs and 4,999.45 µs sampling periods. The recorded 16-bit sensor counters roll over 916 and 915 times. The timestamp helper handles every recorded rollover without a gap. Sensor time remains an uncalibrated estimate: the test does not correct the modeled clock drift or prove physical synchronization.

Foot acquisition starts before shank acquisition, leaving eleven foot samples in its FIFO before the EMG capture starts. At the modeled stop, one newly generated foot packet is still buffered and no shank packet is pending. Saved plus pending packets equal generated packets for both sensors. Pending packets are explicitly counted rather than represented as recorded measurements.

The six native check groups also cover configuration readback, FIFO overflow and insufficient receive capacity, modeled battery calibration API calls, plausible wrong serial-mode codes and ignored conversion triggers/BUSY stuck low. The fault assertions execute after the saved normal session; they are native driver checks rather than injected failures in that session file.

See [summary.json](summary.json), [quality.json](quality.json), [execution.txt](execution.txt) and [capture-artifacts.json](capture-artifacts.json). The full 32,260,800-byte binary recording and roughly 59 MB of CSVs are retained locally at `work/virtual-audit/continuous-driver-check-60s`; hashes are included here to keep the downloadable package compact. The reduced [signal plot](signals.png) comes from the real converter.

This executes actual production peripheral drivers, serializer and timestamp helper under ideal native peripheral APIs. It does not execute the production FreeRTOS recorder, SDMMC hardware, Wi-Fi radio or an assembled analog circuit. It is a 60-second logical driver/format check, not a hardware or scheduler endurance measurement.
