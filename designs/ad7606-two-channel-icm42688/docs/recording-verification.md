# Recording, shutdown and recovery

Project lead: Muttakin Rahman · 1 October 2026, updated 10 October 2026 · AD7606 / two EMG inputs / ICM-42688-P

**The updated recording firmware passes 38 native control-flow cases: 19 for the breadboard and 19 for the compact PCB.** The 38 cases were rerun on source sets 1.7 and 1.8, whose queue-overflow case now needs 20,481 queued records. All seven current v1.8 laboratory profiles, including three recording and four diagnostic builds, compile with ESP-IDF v5.4.2. These native checks exercise the current recorder and serializer with explicit API shims. The [current integrated report](integrated-verification.html) adds actual recorder/FatFS/lwIP execution with modeled peripherals; its full matrix remains incomplete. The [seven earlier diagnostic scenarios](virtual-verification.html) remain historical evidence. None establishes physical SD or radio performance.

## What was corrected

An acquisition worker could finish and delete itself after a fault. The recorder retained that task handle and later notified it during shutdown. Both workers now signal completion and suspend; the recorder waits for their suspended state, deletes them and clears the handles. A latched fault stops further worker acquisition. This follows the known-state task-deletion pattern in [Espressif's ESP-IDF v5.4.2 guide](https://docs.espressif.com/projects/esp-idf/en/v5.4.2/esp32s3/api-reference/system/freertos_idf.html#deletion).

The previous combined IMU stop expression could skip stopping the shank device if the foot stop failed. Both stop calls are now attempted independently, and either failure produces a sensor fault.

Previously the normal END record could reach the Wi-Fi queue before the final SD write, sync and close checks. The recorder now syncs queued data before writing END and publishes its wireless stop verdict after all final filesystem checks. A final failure produces reason 1 and a visible error indication. Successful SD and wireless END records retain identical timestamps, counters and bytes.

## Historical FreeRTOS lifecycle execution in Wokwi

A separate earlier ESP32-S3 simulation includes the then-current v1.4 recorder source and executes its actual task functions, fault latch and join/retire helpers using ESP-IDF v5.4.2 FreeRTOS. Three families each complete 100 cycles: normal shutdown, workers already suspended after a fault, and a partial task set with only the EMG worker. **All 300 cycles pass**, with no assertion or simulator panic. [Serial log](../simulations/recorder-tests/esp32/results/serial.txt) · [execution summary and binary hashes](../simulations/recorder-tests/esp32/results/summary.json).

This lifecycle image uses stub peripheral entry points and does not acquire from the AD7606, service SDMMC or transmit Wi-Fi. It tests task coordination on the simulator's real RTOS implementation. It is not a hardware recording image and is kept outside the seven laboratory firmware profiles. Its tested image remains preserved, and its exact [tested source snapshot](../simulations/recorder-tests/esp32/tested-sources-20260930/main.c) is retained. Current acquisition changes have not been rerun through this 300-cycle image; its result must not be presented as a fresh v1.6 whole-system test. The earlier seven ADC/IMU diagnostic scenarios have their own [preserved tested source/image snapshot](../simulations/wokwi/tested-diagnostic-20260930/manifest.json).

The initial test assumed suspension within 10 ms, shorter than the EMG notification wait of 20 ms. The corrected harness waits for completion/state with a 100 ms deadline. The [failed attempt](../simulations/recorder-tests/esp32/results/before-harness-wait-fix/README.md) is retained; this was a test timing correction, with no further production-source change.

## Test coverage

| Case family | Injected condition | Required observation |
|---|---|---|
| Normal capture | 260 known-code EMG frames, six FIFO packets per IMU | Exact record counts; valid CRCs; no detected sample loss; matching SD/live END |
| Interrupted and short writes | EINTR and repeated 333-byte writes | Original record stream is reconstructed without loss or duplicate bytes |
| Worker finishes before join | Timing fault before recorder cleanup | No notification to a deleted task; both stacks reclaimed; reason 6 |
| Task creation | Missing EMG task or missing IMU task | Created tasks cleaned up; start failure visible; no successful session END |
| Queue overflow | Capacity exceeded through production enqueue | Fault latched; dropped counter increments; reason 2; converter reports loss |
| Storage writes | Failed, zero-byte or partially completed data write | No retry from an unknown continuation offset; no SD END; wireless reason 1 |
| Header write/sync | Initial filesystem operation fails | Acquisition never starts; error indication; no live successful session |
| Final data sync | Sync fails before END | No SD END; wireless reason 1 |
| END sync or close | Failure after END bytes become visible | Error indication and wireless reason 1; readable END alone cannot prove persistence |
| IMU shutdown | Foot stop fails | Shank stop still attempted; reason 3 |
| USB | Attached before start or detected while recording | Start refused or recording ends with reason 7 |
| Low battery | Three consecutive low readings | Recording stops with reason 4 |
| Full card | Free-space gate fails after recording starts | Storage fault; wireless reason 1 |

Production metadata is now built by `firmware/main/metadata.c`: 1,301 bytes for the PCB and 1,308 for the breadboard, including the new `record_queue_entries` field. Source set 1.7 raises the AFW1 metadata limit from 1,280 to 1,400 bytes, so a metadata datagram (1,432 bytes) still fits one 1,500-byte Wi-Fi MTU. A host test compiles `metadata.c` for both profiles and fails if either comes within 64 bytes of the limit. (Source set 1.6 used 1,279 of 1,280 bytes on the breadboard.) The test decodes this exact JSON through the laptop protocol and checks the two enabled channels and GPIO38/47 SD distinction.

[Machine-readable control results](../simulations/recorder-tests/results/summary.json) · [before-fix assertions](../simulations/recorder-tests/results/before-fix.json) · [test source and reproduction](../simulations/recorder-tests/README.md) · [normal synthetic recording](../simulations/recorder-tests/results/breadboard/normal/simulated.afolog) · [normal quality report](../simulations/recorder-tests/results/breadboard/normal/quality.json)

## Interpret the stop indication

| Reason | Meaning | Laboratory action |
|---|---|---|
| 0 | Normal requested stop; final filesystem API calls succeeded | Wait for recording LED to turn off, then remove power/card and convert the file |
| 1 | Storage write, sync, close or free-space failure | Check card supply and contacts; preserve original file and recovery output; never treat the session as a clean recording |
| 2 | Acquisition queue overflow | Investigate write latency and contention; retain loss counters |
| 3 | Sensor communication, FIFO or shutdown fault | Return to ADC/IMU diagnostics |
| 4 | Low-battery stop | Measure rail behavior; recharge the pack externally with no person attached |
| 5 | Configured session-duration limit | Check recorded duration and restart deliberately |
| 6 | Acquisition timing fault | Scope conversion/read timing under load |
| 7 | USB detected | Disconnect USB before a new battery-powered recording |

The error LED is set for every abnormal stop or failed finalization. Best-effort Wi-Fi can lose the END packet; an absent wireless verdict is not permission to infer success. Save the receiver's gap/error report and compare it with the SD conversion.

## Limits and next laboratory check

The native tests are deterministic control-flow execution, not an ESP32 scheduler or electrical simulation. Synthetic records enter production enqueue; they do not pass through physical ADC/IMU acquisition. Filesystem shims model return values and partial writes, not a card's flash controller or persistence guarantees. UDP packet encoding/decoding is tested; radio transmission is not.

The converter's `session_finalized` field means that END was decoded. A sync or close error can still leave END among the readable bytes. File contents alone cannot certify persistence or healthy hardware. Retain the physical error indication and live/serial fault evidence alongside each laboratory trial. The existing format and legacy decoder remain unchanged.

For stage 7, repeat normal stop/start, full-card, interrupted-power and recovery tests using synthetic inputs with no person attached. Stage 8 adds wireless load while the SD record continues. A measured 60-minute continuity run and two-hour battery runtime remain required. Use the [short staged lab sequence](lab-quickstart.html) and record real results before recommending a PCB order.

## Current integrated acquisition checks

The preserved v1.5 run wakes the ADC task from the conversion timer and waits for BUSY with a bounded deadline. IMU estimates use sensor counter deltas after the first FIFO anchor, avoiding burst-boundary timestamp regressions. The [integrated report](integrated-verification.html) covers real FreeRTOS tasks, production C drivers, a FatFS block fixture and actual lwIP UDP loopback together. Ten cases completed with full CLI/firmware passes, and nominal firmware/file/UDP checks pass despite optional trace-download failure. The battery export is partial and four cloud cases were unexecuted because of quota. Deliberately lost wireless END remains unconfirmed; it is never reconstructed as a successful stop.

Current v1.6 additionally requires BUSY assertion during CONVST to reject missing-conversion/stale-data faults and keeps session buffers outside the startup compiler frame. All 18 current-image integrated cases now pass in Wokwi’s web editor, with complete converter/live-decoder checks. Current laptop tests report preview/packet gaps accurately and preserve the received measurement bytes. The ten complete cases and nominal capture described above remain the [preserved v1.5 evidence](../simulations/integrated-recorder/tested-source-1.5/manifest.json), not relabeled current execution. Read the [current integrated report](integrated-verification.html) for the new matrix and its physical/model limits.
