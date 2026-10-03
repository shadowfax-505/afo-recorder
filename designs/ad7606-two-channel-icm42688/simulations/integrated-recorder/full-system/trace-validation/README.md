# Digital timing capture

Muttakin Rahman · AD7606 · two EMG channels · two ICM-42688-P sensors · 3 October 2026

The complete recorder runs in Wokwi with an **input-only virtual instrument** attached. The instrument observes the actual simulator pin transitions; it neither drives a bus nor generates ADC/IMU data. Recorder firmware and the original sensor-model C files are unchanged. The instrument is project-authored and independently tested; it is not a manufacturer model or physical measuring device.

## Results

The [actual browser capture](probe-run/result.json) passes recording, converter, live decoding and digital pin checks. All **10,041 conversions and reads** match the saved EMG count. Each ADC read has **128 rising and 128 falling clocks**, the expected signed eight-word order, and no read while BUSY is high. The first two reads were also decoded independently from **611 captured pin changes**. First/last frame snapshots and aggregate checks cover the acquisition run.

| Observed virtual quantity | Result | Acceptance used |
|---|---|---|
| Mean CONVST rate | 7,983.860 Hz | 8,000 Hz ±1% |
| Trigger intervals | 122.250–128.262 µs | 125 µs ±5 µs |
| CONVST high time | 1.483–1.484 µs | At least 25 ns; at most 10 µs in this nominal check |
| Behavioral BUSY duration | 4.000 µs | 4.000 µs for the configured model |
| Falling read-clock interval | 125 ns, across 1,275,207 intervals | 125 ns ±1 ns |
| SPI transfer duration in saved frame snapshots | 16.000 µs | 128 clocks at 8 MHz |
| Foot/shank interrupt periods | Both 5.000 ms | 200 Hz for the configured models |
| Foot/shank interrupt pulse widths | Both 10.000 µs | 10.000 µs for the configured models |
| Interrupts during the ADC trigger window | 252 / 252 | Counts consistent with window duration and independent phases |

[Timing plot](probe-run/adc-timing.png) · [Raw rendered Chips Console](probe-run/chips-console.txt) · [Partial edge CSV](probe-run/sampled-edges.csv) · [Partial derived VCD](probe-run/sampled-edges.vcd) · [Observation log](observations.json).

The two expected discarded SPI reads occur during RESET: one in initial `adc_bus_init` and one when `start_recording` calls `adc_configure` again. Neither is an EMG measurement. The separate one-shot diagnostic has a different startup count; its older acceptance gate remains unchanged.

The probe's raw `wrong_idle_clock` field counts **10,043 assertions with virtual SCLK low** at the CS edge. This is retained as a simulator observation, not hidden or renamed in the captured data. Falling-edge decoding and all active read clocks pass. **Physical clock idle polarity and setup/hold margins remain unqualified.** Do not alter the physical design based only on the inactive GPIO state in this simulator.

## Capture limits

Two complete-scene attempts did not return a native logic-analyzer download through the browser automation. Their original inputs, serial captures and status are retained in `attempt-1` and `attempt-2`. They are not passed waveform checks.

The partial VCD here is derived from **actual observer events**, with its origin in the header. It covers the first two complete ADC reads, plus a leading BUSY edge before the next CONVST callback. It is **not** a retrieved full-session Wokwi logic-analyzer VCD. All-frame decoding/timing counters are separate from that partial edge capture.

The nominal full-system substitutes still apply: behavioral ADC/IMUs, separately simulated analog response, PSRAM in place of SDMMC/card hardware, internal UDP subscriber in place of external radio transport, and injected battery/USB state. No power, analog-noise, module-strapping, card, radio, thermal or runtime result is measured here.

## Run the instrumented scene

1. Open the [saved complete recorder project](https://wokwi.com/projects/476662256690643969). The saved public scene is preserved; these probe additions are optional.
2. Download `digital-timing-wokwi.zip` from the [digital timing guide](../../../../docs/digital-timing.html), then extract it.
3. In the Wokwi file menu, select **Upload file(s)…** and upload `probe.chip.c` and `probe.chip.json` from `integrated-recorder/full-system/trace-validation/`.
4. Replace the editor's `diagram.json` with this folder's copy. There should be **38 parts and 89 connections**, including the explicitly labeled input-only probe.
5. Focus an editor, press **F1 → Upload Firmware and Start Simulation…**, and choose `integrated-recorder/firmware/merged.bin`. Check ELF prefix **aabb34031**. This image is simulation-only; never flash it onto hardware.
6. Wait for complete AFO/UDP exports and `INTEGRATED_COMPLETE,case=0` in **Serial Monitor**. Open **Chips Console** and scroll to `PROBE_SUMMARY`.
7. Retain both original console texts. A missing summary, missing pin events, a counter mismatch or resumed conversions after the summary must fail qualification.

The small bundle provides all scene/model sources and the exact simulation image. Web Wokwi compiles the C probe; the browser's resulting WASM hash is not exposed here. The separate local CLI compilation is recorded only as a build check, and that WASM is not redistributed as the executed web image.

## Reproduce the assessment in a complete project checkout

```sh
python3 test_probe.py
python3 assess_probe.py probe-run
python3 export_edges.py probe-run
```

The first command uses a native C event harness with **10 test groups and 12 injected fault variations**. These harness edges are synthetic and test the instrument itself. The browser run supplies recorder evidence. Checks include short clocks, swapped words, missing BUSY, reading while busy, wrong clock sequencing, reset/priming mistakes, slow clocks/triggers, missing interrupts, partial frames, late triggers, truncated summaries and good summaries paired with bad raw data.

Assessment also verifies the frozen 31-file recorder manifest, the pre-run diagram copied from the editor, probe source hashes, actual boot identity, exact AFO/UDP exports, saved counter continuity and host decoding. The complete checkout is required for the strict assessor's shared host tools. Plotting requires Matplotlib.
