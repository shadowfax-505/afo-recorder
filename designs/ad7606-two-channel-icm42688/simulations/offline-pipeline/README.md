# Offline analog-to-file checks

Run with Python 3, a C11 compiler, NumPy and Matplotlib:

```sh
python3 run.py
python3 run_queue.py
python3 run.py --seconds 60 --output /tmp/recorder-continuous-60s --compact-directory results/continuous-60-seconds
```

The first command compiles the actual production `adc_ad7606.c`, `sensors.c` and `format.c`. It uses the actual `imu_timing.h` helper. Ideal ESP-IDF peripheral API models feed the ngspice-derived ADC codes and independent IMU FIFO clocks. The generated binary file then passes through the real converter. Results include a synthetic recording, CSVs, plots, source hashes and known-code comparisons.

The default two-second run checks all 16,000 EMG frames and both sensor identities. Register readback errors, FIFO overflow, receive capacity, modeled battery calibration API calls and plausible wrong-mode ADC codes are also exercised. An ignored conversion pulse or a BUSY line that never rises must fail explicitly; plausible stale ADC codes must not count as a successful conversion. Disabled ADC outputs remain zero and never appear as additional EMG channels.

The separate 60-second run checks 480,000 EMG records against every repeated ngspice-derived ADC code, both IMU identities and more than 900 rollovers of each 16-bit sensor counter. The real converter validates every record CRC, stream counters, sample timing and CSV scaling. Sensor FIFO packets still buffered at the modeled stop are counted separately; they are not called saved measurements. The first sensor starts before the second, so the captured stream includes its startup FIFO lead. Full binary and CSV evidence can occupy about 87 MB and remains in the selected output directory. The package includes [the compact results](results/continuous-60-seconds/summary.json), [artifact hashes](results/continuous-60-seconds/capture-artifacts.json) and [a reduced plot](results/continuous-60-seconds/signals.png). The original two-second result files remain preserved in [before-busy-confirmation](results/before-busy-confirmation/README.md); the current short run was regenerated against the updated driver.

This is native, ordered C execution with ideal peripheral models. It does not run `main.c`, a real RTOS scheduler, SDMMC or radio. Modeled IMU transfer windows use a separate bus budget; host calls do not emulate CPU/interrupt contention. Timestamp estimates and synthetic IMU clock drift are not physical synchronization measurements.

The queue command models arrivals, 128-record writes, assumed throughput and deliberate stalls. Four one-hour event-count cases pass; the 350 ms stall and a 500,000-byte/s writer exceed capacity and explicitly overflow. No one-hour binary recording or firmware endurance test executes here. The assumed writer is not an SD-card specification or measurement.

See [the combined evidence report](../../docs/integrated-verification.html) for the distinction between these local checks and actual ESP32 firmware execution in Wokwi.
