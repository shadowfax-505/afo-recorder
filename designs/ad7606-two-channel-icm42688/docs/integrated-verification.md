# Integrated recorder verification

Project lead: Muttakin Rahman · 1 October 2026 · AD7606 / two EMG inputs / ICM-42688-P

**All 18 current v1.6 integrated cases pass in Wokwi’s web simulator, with complete serial exports checked by the actual converter and live decoder.** The nominal run saves 10,041 EMG frames, 263 foot and 252 shank records, with no detected saved-sample loss or acquisition errors. This is actual ESP-IDF execution with documented peripheral substitutions, not measured hardware performance. The nominal best-effort preview drops one EMG frame and reports it explicitly; the independent saved recording is complete.

Execution and review corrected delayed ADC servicing, backwards IMU time estimates, missing conversion acknowledgement and startup stack allocation. The full **current integrated case matrix** passes; physical acceptance and a current downloaded VCD trace remain unqualified. Earlier failed or partial attempts are retained rather than relabeled.

This report covers this configuration only. The other five designs retain their previous files and validation status. Electrical connections, PCB geometry and manufacturing files have not changed in this refinement.

[See the complete system](whole-system.html): the physical assembly and a separate saved Wokwi scene include power, both EMG paths, both IMUs, storage, controls and laptop context. The expanded scene passed an additional nominal run. The eighteen-case results below retain their original protocol-fixture diagrams.

**3 October follow-up:** a complete-scene [digital pin observer](digital-timing.html) passes 10,041 ADC trigger/read checks and both 200 Hz IMU interrupt streams. The [saved-data audit and interpretation guide](data-interpretation.html) independently compares 21,116 original records across two captures with every exported CSV row, verifies channel identity and nominal units, and confirms byte parity between received preview records and the saved file. Native full-session VCD download and hardware timing remain unqualified.

## Tested versions

Current laboratory firmware is **ad7606-2ch-1.6**; all seven profiles compile. The separate integrated image executes the production recorder, sensor drivers, serializer and Wi-Fi task with fixture wrappers. Its [31-file source/configuration/model/image manifest](../simulations/integrated-recorder/firmware/manifest.json), boot ELF identifier and each saved diagram identify the tested build. The current [18-case web ledger](../simulations/integrated-recorder/results/web-current/summary.json) is distinct from the pre-web quota-refused candidate.

The earlier **v1.5** cloud ledger has 16 cases and remains incomplete. Its [exact tested snapshot](../simulations/integrated-recorder/tested-source-1.5/manifest.json), failed attempts, partial battery export and CLI transport errors are preserved. A current web success does not change those historical outcomes. Newly rebuilt laboratory binaries have not been flashed; the instrumented integrated image is a different binary.

Wokwi officially supports [ESP32-S3 and custom firmware upload](https://docs.wokwi.com/guides/esp32) and [custom C chip models](https://docs.wokwi.com/chips-api/getting-started). The supported web-editor path completed despite CLI CI quota refusal. Its ADC C source inlines the stimulus header and removes only the header-specific pragma; callbacks and values are unchanged. [Reproducible web files and transformation manifest](../simulations/integrated-recorder/web/README.md).

## What executed together

The Wokwi image includes the production `main.c`, AD7606 and ICM drivers, serializer and Wi-Fi task. Actual ESP-IDF v5.4.2 FreeRTOS tasks acquire data, queue records, write and synchronize a real FatFS filesystem, initialize the ESP32 access point, and send actual AFW1 datagrams through lwIP. The real laptop decoder and converter process the exported bytes.

Four substitutions define the scope:

| Interface | Executed implementation | Substituted part |
|---|---|---|
| ADC and IMUs | ESP32 SPI peripheral, production drivers, conversion timer and interrupt handling | Project behavioral AD7606/ICM chip models; ideal digital signals |
| Storage | Production writes/sync/close, real FatFS and VFS, fault handling | Sparse PSRAM block medium replaces the card and SDMMC transport |
| Wireless | Actual access-point initialization, Wi-Fi task, lwIP UDP and laptop decoding | A UDP subscriber inside the emulated MCU replaces the laptop’s radio link |
| Battery and controls | Production start/stop, USB inhibition and low-battery logic | Defined voltage readings and button/USB fixture inputs |

Wokwi’s supplied microSD model uses SPI; it cannot validate this recorder’s unchanged SDMMC wiring. [Wokwi microSD documentation](https://docs.wokwi.com/parts/wokwi-microsd-card). Access-point startup and UDP loopback do not establish over-the-air reception. [Wokwi networking documentation](https://docs.wokwi.com/guides/esp32-wifi).

The simulation-only binary has additional trace instrumentation and fixture wrappers. **Never flash it onto the recorder.** Laboratory images are under `firmware/builds/`; simulation images are under `simulations/`. [Executed v1.5 source, configuration and image hashes](../simulations/integrated-recorder/tested-source-1.5/manifest.json).

## Corrections

### Conversion timing

The original recorder waited for the falling BUSY interrupt. In the combined simulation that notification arrived after the next 125 µs deadline, after about 2,385 valid frames. The driver correctly refused to overwrite an unread conversion, but continuous recording stopped. The failed capture remains in the package.

The acquisition timer and GPIO service now belong to core 1. After each CONVST pulse, the timer notifies the EMG task directly. The task checks BUSY before starting SCLK and fails after an 80 µs readiness wait. The next-period unread-result guard remains active. SPI still reads all eight 16-bit words through DOUTA in mode 2; only EMG1 and EMG2 are exported. A conversion deadline failure reports timing reason 6.

This removes the second interrupt handoff. It does not prove physical scheduling margins. Higher-priority interrupt experiments caused kernel failures and were reverted; those failed attempts are retained. The final combined run uses the ordinary interrupt priority and an enabled task watchdog.

### Missing BUSY assertion — current v1.6

A disconnected/stuck-low BUSY pin or ignored CONVST pulse could previously leave BUSY low and permit a serial read of stale conversion words. The current driver requires BUSY to be high at the end of the existing 1 µs CONVST pulse. This is consistent with the [AD7606 Rev G timing limits](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf): BUSY asserts within 45 ns, while the shortest listed conversion is 3.45 µs with oversampling disabled. A missing assertion latches a timing fault before accepting a frame. The later bounded BUSY-low wait still rejects stuck-high or delayed completion.

Sixteen native ADC groups and the local C pipeline exercise this correction, including independently injected stuck-low BUSY and ignored CONVST. This is mocked API evidence. Current v1.6 web execution independently rejects stuck-high BUSY, stuck-low BUSY and ignored CONVST with reason 6, an ADC error and zero accepted EMG frames. Earlier captures establish their own v1.5 behavior only. Physical timing and voltage checks remain required.

### IMU time reconstruction

Re-anchoring every FIFO burst to the latest interrupt created 35 backwards host-time estimates in one otherwise complete capture. An IRQ and a FIFO-count read can observe different sample boundaries.

The recorder now anchors the first estimate and advances subsequent estimates using the stored 16-bit sensor timestamp increments. Each IMU keeps its own state. Zero or implausible increments, backwards read times, and an unread interval spanning an entire 65,536 µs rollover are rejected explicitly. Missing counter intervals remain flagged. An IRQ arriving during a read indicates timing uncertainty; it does not by itself establish missing samples.

The raw FIFO packet, IRQ anchor and read window remain in every record. `imu_time=fifo_delta_first_irq` identifies the revised method. Estimates remain uncalibrated: sensor-clock drift, the initial anchor error and filter delays are not corrected. Legacy files retain their original interpretation.

The wireless sender also collects short batches rather than sending almost every EMG record in a separate datagram. Its collection target is 2 ms; RTOS scheduling and transport can add latency. Wi-Fi remains best-effort and cannot block or replace the saved recording.

## Current v1.6 integrated results

Every case below completed on the same current ESP32-S3 image. The assessor verifies the boot image identifier and diagram, contiguous export offsets, exact terminators, binary CRCs, channel identities, known ADC codes, converted quality and the actual AFW decoder state. Refusals deliberately produce no recording. Fault cases pass when they expose the specified abnormal outcome, not when they appear loss-free.

| Case | Current observation | Result |
|---|---|---|
| normal | 10,041 EMG / 263 foot / 252 shank; saved END 0; complete SD stream; one explicit preview-frame drop | [PASS](../simulations/integrated-recorder/results/web-current/normal/result.json) |
| write-delay-50ms | Same saved counts; no saved drops or acquisition errors; queue peak 421 | [PASS](../simulations/integrated-recorder/results/web-current/write-delay-50ms/result.json) |
| queue-stall-350ms | Reason 2; queue reaches 2,048; one explicit dropped record | [PASS](../simulations/integrated-recorder/results/web-current/queue-stall-350ms/result.json) |
| storage-write-error | Reason 1; converter identifies the abnormal/unfinalized saved stream | [PASS](../simulations/integrated-recorder/results/web-current/storage-write-error/result.json) |
| usb-attached-during-recording | Reason 7; acquisition stops and abnormal END is retained | [PASS](../simulations/integrated-recorder/results/web-current/usb-attached-during-recording/result.json) |
| battery-low | Reason 4; 24,005 EMG; complete file and UDP export; no acquisition errors | [PASS](../simulations/integrated-recorder/results/web-current/battery-low/result.json) |
| adc-stuck-busy | Reason 6; ADC error; zero EMG | [PASS](../simulations/integrated-recorder/results/web-current/adc-stuck-busy/result.json) |
| imu-fifo-overflow | Reason 3; overflow counter; zero accepted EMG | [PASS](../simulations/integrated-recorder/results/web-current/imu-fifo-overflow/result.json) |
| imu-missing-interrupt | Reason 3; IMU error; no later clean session | [PASS](../simulations/integrated-recorder/results/web-current/imu-missing-interrupt/result.json) |
| no-wireless-subscriber | 10,043 EMG saved; no subscriber datagrams; saved stream complete | [PASS](../simulations/integrated-recorder/results/web-current/no-wireless-subscriber/result.json) |
| wireless-packet-loss | 158 datagrams discarded and 158 decoder gaps; SD complete; received END 0 does not hide missing measurements | [PASS](../simulations/integrated-recorder/results/web-current/wireless-packet-loss/result.json) |
| interrupted-recording | Directory reopened from modeled disk; no END; converter/live decoder retain unfinalized state | [PASS](../simulations/integrated-recorder/results/web-current/interrupted-recording/result.json) |
| storage-mount-failure | Initialization refuses recording; no new file | [PASS](../simulations/integrated-recorder/results/web-current/storage-mount-failure/result.json) |
| full-card-refusal | Start refuses recording; no new file | [PASS](../simulations/integrated-recorder/results/web-current/full-card-refusal/result.json) |
| filtered-synthetic-emg | 10,041 EMG; every code matches the ngspice-derived quantized stimulus, in channel order | [PASS](../simulations/integrated-recorder/results/web-current/filtered-synthetic-emg/result.json) |
| absent-shank | Initialization refuses recording after missing shank identity | [PASS](../simulations/integrated-recorder/results/web-current/absent-shank/result.json) |
| adc-busy-stays-low | Reason 6; ADC error; zero EMG; no stale-word acceptance | [PASS](../simulations/integrated-recorder/results/web-current/adc-busy-stays-low/result.json) |
| adc-trigger-ignored | Reason 6; ADC error; zero EMG; no stale-word acceptance | [PASS](../simulations/integrated-recorder/results/web-current/adc-trigger-ignored/result.json) |

[Current nominal quality](../simulations/integrated-recorder/results/web-current/normal/converted/quality.json) · [current explicitly synthetic recording](../simulations/integrated-recorder/results/web-current/normal/simulated-recording.afolog) · [filtered signal plot](../simulations/integrated-recorder/results/web-current/filtered-synthetic-emg/converted/signals.svg).

The low-battery fixture now yields during post-recording serial export. Both export terminators completed; the earlier v1.5 partial dump remains partial. This checks the simulated low-voltage response, not measured battery runtime. No current native downloaded VCD is available. The later [pin-observer waveform](digital-timing.html) is a partial capture derived from observed simulated transitions, with separately checked complete-session counters; it does not qualify a native full-session VCD.

### Startup stack correction

The additional Espressif QEMU experiment exposed startup stack pressure: the compiler had inlined session buffers into the startup function used by NVS/network initialization. Keeping `record_session` separate reduces the compiler's startup frame from 2,640 to 352 bytes, while retaining an 8 KiB main stack. All seven profiles were rebuilt, the 38 native control cases rerun, and the current Wokwi matrix executed after this change. This is not measured peak stack usage on hardware.

### Independent offline emulator

The [QEMU experiment](../simulations/qemu-recorder/README.md) retains seven outcomes: three initialization-refusal passes, one generic abnormal-stop pass and three failed qualification cases. Its nominal run cannot meet the unchanged 1 µs BUSY observation and 125 µs sampling deadlines and stops before accepting EMG. Its specific ADC fault paths are not established where scheduler failure can mask injection. **QEMU is not counted as a qualified continuous-acquisition result.** The failed matrix, exact image, substitutions and vendor runtime identity are retained.

## Preserved v1.5 integrated capture results

Sixteen cases were requested. **Ten completed with successful CLI execution and all applicable saved-file/laptop checks.** A separate nominal run completed and passed every firmware/file/UDP check, but its optional VCD retrieval ended with an API transport error. The low-battery run reached the correct saved stop; its UDP export was incomplete. Four cases did not execute because Wokwi exhausted the account’s monthly CI quota. They are not counted as passes.

| Case | Observed result | Status |
|---|---|---|
| Nominal recorder | 10,041 EMG; 263 foot; 252 shank; reason 0; exact known ADC codes; both identities; saved/live END agree | Firmware/file/UDP checks pass; optional VCD download failed |
| 50 ms write delay | 10,041 EMG; no saved-queue drops or ADC errors; complete SD recording; 344 best-effort Wi-Fi queue drops visible | Pass |
| 350 ms write stall | Queue overflow, explicit reason 2 and loss/counter evidence | Pass |
| Storage write error | Reason 1; unfinalized saved stream; wireless storage verdict | Pass |
| USB attached during recording | Explicit reason 7 and finalized abnormal stop | Pass |
| Low battery | 24,005 EMG; reason 4 after consecutive low readings; saved file exported; UDP export incomplete | Partial; whole case unverified |
| Stuck BUSY | Bounded failure; reason 6; no plausible replacement measurements | Pass |
| IMU FIFO overflow | Explicit reason 3 and overflow counter | Pass |
| Missing IMU interrupt | Explicit reason 3; no later clean session | Pass |
| No wireless subscriber | Complete saved recording; no subscriber datagrams | Pass |
| Wireless packet loss | 159 datagrams discarded; 158 observable sequence gaps; saved recording complete; lost live END remains unconfirmed | Pass |
| Interrupted recording | Reopened FatFS directory state lacks END; converter and receiver do not infer finalization | Pass |
| Mount failure | No new cloud execution | Pending quota |
| Full-card refusal | No new cloud execution | Pending quota |
| Filtered synthetic EMG | No new cloud execution; separate local C pipeline passes below | Pending cloud run |
| Absent shank IMU | No new cloud execution; historical diagnostic coverage retained | Pending quota |

The nominal EMG rate derived from ESP32 timestamps is approximately 7,983.87 Hz, within the declared virtual gate of 8 kHz ±1%. Foot/shank counts differ because the sensors start at different times and run independently. All 515 IMU records retain the timing-uncertain flag; none is presented as a calibrated timestamp.

[Complete result ledger](../simulations/integrated-recorder/results/current/summary.json) · [nominal recording](../simulations/integrated-recorder/results/current/normal/simulated-recording.afolog) · [nominal quality report](../simulations/integrated-recorder/results/current/normal/converted/quality.json) · [wireless loss report](../simulations/integrated-recorder/results/current/wireless-packet-loss/result.json).

Losing a wireless END is allowed by a best-effort link. The receiver correctly leaves `ended=false` and `stop_reason=null`; it must not invent a normal stop. The original test incorrectly required END despite deliberately dropping datagrams. Its initial failure and corrected assessment are both retained.

The low-battery fixture emitted idle-watchdog warnings while exporting a large serial dump after recording had stopped, and the 30-second capture limit expired before the UDP export terminator. The saved low-battery file is readable; this does not complete the wireless or whole-case gate. The current fixture yields an RTOS tick between post-recording export chunks, and the runner allows a 120-second simulated export window. The current web battery case now completes both exports; these are harness changes, and the original v1.5 case remains partial.

All captures are synthetic. `.raw` files preserve the unmodified production output, including its original `synthetic=false` metadata field. The companion `.afolog` fixtures explicitly set `synthetic=true`. Neither contains a human recording.

## Local verification beyond the cloud runs

| Check | Result | What it establishes |
|---|---|---|
| Fresh KiCad ERC/DRC | Zero violations and unconnected items | Rules and connectivity, not physical performance |
| Independent net/pad/pin comparison | 390 component pins; 22 firmware GPIOs per profile; no mismatches | Schematic, actual PCB pads and PCB/breadboard GPIO definitions agree |
| Current v1.6 firmware compilation | All seven laboratory profiles compile | Three recording and four diagnostic ESP-IDF builds; hardware images remain unflashed |
| Current v1.6 ADC C driver | 16 groups pass; address/undefined sanitizer rerun passes | BUSY assertion/timeout, ignored CONVST, timer notification, signed order, disabled outputs, unread/late results and restart logic with mocked APIs |
| IMU timestamp helper | Eight groups pass; address/undefined sanitizer rerun passes | Counter rollovers, independent identities, monotonic estimates and rejection of ambiguity |
| Recorder control | 38 cases pass across both profiles | Production start/stop/write/sync/close/fault control with explicit API shims |
| Converter/live/legacy regressions | 40 tests pass | Format, scaling, invalid data, gaps and backwards compatibility |
| Integrated-evidence runner | 16 tests pass | Rejects partial/stale evidence, panics and plausible wrong codes; does not turn quota refusal into a pass |
| Current behavioral ADC model | 12 native groups pass with AddressSanitizer/UndefinedBehaviorSanitizer | Independent API stubs exercise the actual model callbacks; no Wokwi runtime, WASM or production-firmware execution |
| Local analog-to-file pipeline | 60 seconds; 480,000 EMG; 12,009 foot; 12,001 shank; correct known codes; zero regressions or unexplained loss | Actual current C ADC/IMU drivers, timestamp helper and serializer with ideal peripheral APIs; real host conversion |
| ngspice | Both channels agree; 16 tolerance corners; 54 DC/loading cases; analytical error below 0.02 dB | Documented analog surrogate and ideal quantization, not measured noise or op-amp qualification |
| Long queue model | Four one-hour event-count runs pass; 350 ms stall and inadequate throughput correctly overflow | Capacity under assumed write rates/latencies; no firmware or endurance execution |

The local pipeline feeds ngspice-filtered, explicitly synthetic RAW-like signals through the actual C peripheral drivers and serializer. A separate mocked register/FIFO model supplies the IMUs. It also confirms that a wrong serial mode can return plausible `-1` ADC values: known-input qualification is essential because the original AD7606 has no sensor-frame CRC or identity register.

The extended native pipeline covers 60 seconds of ordered C execution at the configured rates. The foot/shank models use +70/−110 ppm clocks, with 916/915 timestamp-counter rollovers respectively. Foot starts earlier and has one generated packet still in FIFO at stop; shank has none pending. All generated-versus-saved counts are explicit. This exercises counter rollover and recording conversion under modeled clocks, **not a 60-second ESP32 scheduler, SDMMC or radio endurance test**. The shorter two-second fixture and its plotted waveform remain available below.

[60-second pipeline evidence](../simulations/offline-pipeline/results/continuous-60-seconds/summary.json) · [current behavioral model checks](../simulations/integrated-recorder/model-test-results.json).

![Synthetic analog-to-file verification](../simulations/offline-pipeline/results/converted/signals.svg)

[Local pipeline evidence](../simulations/offline-pipeline/results/summary.json) · [generated recording](../simulations/offline-pipeline/results/synthetic.afolog) · [analog response](../simulations/results/frequency-response.png) · [queue budget](../simulations/offline-pipeline/results/queue-budget.json).

At 8,000 EMG frames and 400 IMU records per second, 64-byte records consume approximately 537,600 bytes/s before status/header overhead. The 2,048-record queue covers about 244 ms of arrivals. The one-hour model uses an assumed 2 MiB/s writer and specified stalls; it does not measure any card. A two-hour file is nominally about 3.87 GB, including per-second status records, under the [individual FAT32 file limit documented by Microsoft](https://learn.microsoft.com/en-us/windows/win32/fileio/filesystem-functionality-comparison). Actual card latency, free space and recording durability remain unqualified.

The previous seven diagnostic Wokwi scenarios and 300 FreeRTOS join/lifecycle cycles remain historical evidence. Their tested images and sources are preserved separately. The seven newly compiled laboratory profiles have not all been rerun in Wokwi; the current integrated web matrix does not establish that claim. [Historical diagnostic source/image snapshot](../simulations/wokwi/tested-diagnostic-20260930/manifest.json).

## Captured timing audit

Current v1.6 post-processing passes timing checks for all 15 captures with recordings; the other three cases refuse initialization/start. In the current nominal file, trigger intervals span 122–128 µs, trigger-to-read-start is 7–11 µs, reads take 23–29 µs, and recorded completion precedes the next trigger by 89–97 µs. The timestamp-derived rate is approximately 7,983.86 Hz, within the declared 8 kHz ±1% virtual gate. The estimated first-shank/first-foot offset remains 55,001 µs, with 11 additional foot startup packets. These are instrumented file timestamps from ideal behavioral models, not a downloaded logic waveform or calibrated hardware measurement. [Current timing audit](../simulations/integrated-recorder/results/web-current/timing-audit.json).

Nine post-processing test cases pass for the timing auditor, including known nominal evidence, counter rollover, causality, missing-gap flags and rejection of re-anchored or future estimates. This inspects **existing v1.5 captures**; it is not new firmware execution.

In the nominal file, CONVST timestamp intervals span 122–129 µs; trigger-to-read-start is 6–12 µs; recorded read duration is 23–29 µs; read completion precedes the next trigger by 89–98 µs. Both modeled IMU counters advance by 5,000 µs per packet, corresponding to 200 Hz. These observations describe the captured behavioral-model run, not physical interrupt jitter or clock accuracy.

The first shank estimate is **55,001 µs after the first foot estimate**, and foot has 11 additional startup packets. The firmware starts the sensors sequentially, with a 50 ms wait per `imu_start`; their counters have independent origins. This startup offset is explicit rather than called missing data. It does not calibrate foot/shank synchronization or EMG-to-IMU alignment. All reconstructed IMU estimates remain flagged uncertain.

The retained stuck-BUSY trace contains two initialization reads before the first CONVST, then one trigger and no post-trigger ADC read. RESET is not an analyzer channel, so the initialization classification relies on the known driver path rather than observing RESET directly. [Timing audit and raw-file hashes](../simulations/integrated-recorder/results/current/timing-audit.json).

## Laptop receiver, API and live display

Current v1.6 AFW datagrams pass through a real loopback UDP socket into the actual receiver subprocess and HTTP API. Its live page is checked in the browser, reception is paused to verify the unavailable-link state, and the archived measurement bytes are compared exactly with received AFR records before conversion. Only metadata is marked synthetic. Corrupted CRCs and duplicate packets are rejected without adding measurements.

| Current replay | Received records | UDP gaps | Measurement / ending result |
|---|---|---|---|
| Nominal | 10,557 | 0 | One explicitly reported preview EMG drop; saved SD has all 10,558 records; received END 0; laptop converter reports the one missing EMG frame |
| Deliberate packet loss | 9,034 | 158 | 1,457 EMG, 34 foot and 33 shank sequence gaps; received END 0; laptop converter still reports loss |

Both replays pass byte preservation, actual socket/API, browser, fault rejection and archive checks. Both laptop conversions intentionally return the quality-warning exit code 2. Passing this test means missing data is reported accurately; it does not mean wireless capture is loss-free. The source SD recordings remain complete.

Earlier v1.5 loss replay remains evidence of a lost END: `ended=false`, unknown reason and explicit missing-END quality. The new loss run delivered END, so its ending is retained without concealing gaps. The replay test now derives gaps and ending from the actual source rather than assuming a fixed packet-discard outcome. Its initial incorrect expectation and earlier runner are preserved.

The page shows EMG1/2 only, correct approximately 1 V/2 V scaling, separate foot/shank values, timing uncertainty and a synthetic-data banner. No physical radio connection was exercised. [Current laptop results](../simulations/laptop-tests/results/current-1.6-final/summary.json) · [reproduction guide](../simulations/laptop-tests/README.md).

![Current synthetic packet-loss replay](../simulations/laptop-tests/results/current-1.6-final/wireless-packet-loss-browser.png)

## What is still required

The current 18-case integrated matrix passes with the stated models and substitutions. The independent QEMU nominal qualification remains failed, and no new downloaded VCD or fresh execution of every laboratory diagnostic binary is claimed. **Physical acceptance has not passed.** The package keeps those limitations, historical failures, source/image hashes and empty measured-results sheets visible.

Simulation cannot determine the received RoboticsBD board’s actual serial straps, VIO, reference or output voltage, nor real analog noise, protection behavior, power startup, temperature, crosstalk, cable integrity, radio performance, SDMMC reliability or battery runtime. The first physical gate remains ADC-module voltage/mode/reference qualification before ESP32 signal connections. Lab and human-testing prerequisites are unchanged; no board order is recommended or placed.

Follow the [variant-specific lab sequence](lab-quickstart.html) when instruments become available. In the meantime, the [integrated harness](../simulations/integrated-recorder/README.md) and [offline pipeline](../simulations/offline-pipeline/README.md) can reproduce the checks within their declared limits.
