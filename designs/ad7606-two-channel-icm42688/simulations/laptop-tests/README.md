# Laptop reception and display test

This test replays the actual AFW datagrams exported by the integrated ESP-IDF simulation through the production laptop receiver. It launches `host/live_receiver.py` in a separate process, connects through a real loopback UDP socket, calls its HTTP API, loads its live page in a browser, closes the receiver cleanly, and runs the production converter on the resulting laptop recording.

The input is simulated data. The replay changes only `synthetic=true` in each metadata packet and recomputes that packet's CRC. It preserves every measurement record, sequence number, timing flag and missing packet from the source capture. Neither the test nor its screenshots represent physical sensor or radio measurements.

## Run it

From this recorder package:

```sh
python3 simulations/laptop-tests/run.py
```

That runs the receiver, HTTP, archival and converter checks without a browser. To include the browser, pass an installed Playwright CLI executable or its wrapper:

```sh
python3 simulations/laptop-tests/run.py --browser-cli /path/to/playwright-cli
```

Use a Python environment with the dependencies in `host/requirements.txt` installed. The script uses kernel-assigned UDP and HTTP ports on localhost; it does not join a network or use a token. Results are written beneath `simulations/laptop-tests/results/`. Browser screenshots are saved in that result directory's `output/playwright/` folder.

## What is checked

| Check | Nominal capture | Capture with dropped packets |
|---|---|---|
| Received records | 10,558 | 9,029 |
| Missing UDP packets | 0 | 158 |
| Enabled EMG plots | EMG1 and EMG2 only | EMG1 and EMG2 only |
| Known ADC values | 6,554 and 13,107 codes, displayed as approximately 1 V and 2 V | Same known values, with visible plot breaks at missing samples |
| Foot/shank identity | Separate recorded axes and sample counters | Same identities retained |
| Wireless END | Present; stop reason 0 | Absent; `ended=false`, stop reason remains null |
| Receiver archive | Original measurement bytes preserved exactly | Original received measurement bytes preserved exactly |
| Corrupted CRC / duplicate datagram | Rejected; measurement count unchanged | Rejected; measurement count unchanged |
| Link stops sending | Browser reports that the link is unavailable | Browser reports that the link is unavailable |
| Converter | Finalized, no detected sample loss | Missing END and explicit sample gaps |

The nominal converter reads 10,041 EMG, 263 foot and 252 shank records, plus status and END. The loss capture retains explicit gaps of 1,449 EMG samples and 38 samples from each IMU. The receiver does not insert replacement samples or infer an END it did not receive. The live page includes a synthetic-data banner, uses the actual local HTTP API, draws only two EMG channels, and reports delivery faults.

`results/summary.json` includes the exact host-source hashes, original UDP-capture hashes, measurement-body hashes and case results. The screenshots and browser DOM summaries show the rendered page. The compact API evidence intentionally omits raw UDP payloads and full sample arrays; the API was also checked for raw payload or credential fields. Temporary laptop recordings are deleted after their byte-for-byte comparison and conversion. The original source captures remain in the integrated-recorder results.

## Limits

Loopback UDP checks the real laptop socket, framing, capture, HTTP and display code. It does not reproduce the physical ESP32-to-laptop radio, access-point connection, RF interference or operating-system network conditions under an actual wireless session. Replaying approximately one thousand packets per second is a controlled functional test, not a measured wireless-throughput or endurance result. The packet-loss scenario comes from the integrated simulator's deliberate discard behavior. All converter results remain `research_ready=false`.
