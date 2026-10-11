# Breadboard updates from simulation

**AD7606 · two EMG inputs · two ICM-42688-P carriers.** The simulation findings now inform the [guided assembly](../viewer/build.html), [wire tables](build-guide.html) and [short lab sequence](lab-quickstart.html). Use the [bench checklist](bench-checklist.csv) to collect physical results and the [probe table](../breadboard/probe-connections.csv) to connect instruments. Every measurement row starts as **NOT TESTED**.

The existing connections already match the corrected firmware. This update adds specific checks and explanations at those connections. The current breadboard firmware is `ad7606-2ch-1.8`; its seven compiled profiles and source hashes were checked again. None of those laboratory images has been flashed to an assembled recorder. Wokwi executed a separate instrumented 1.6 image, not yet repeated for 1.7 or 1.8, with storage and wireless substitutions described in the [verification report](integrated-verification.html).

## What to do differently at the bench

| Finding | Action in the breadboard build | Stage |
|---|---|---|
| A late read could otherwise reuse or relabel a previous conversion. | Use the current firmware. It checks BUSY assertion, rejects unread/overlapping conversions, and stops on an ADC timing fault. Scope CONVST, BUSY, CS and SCLK together; a repeated plausible DC code alone is insufficient evidence. | 3 |
| Both conversion groups must start together. | Verify continuity from GPIO11 through DIST1 a29/b29/c29 to **both CVA and CVB**. Capture the same rising edge at both module terminals. | 3 |
| Two-channel export still requires the full serial frame. | Read all eight 16-bit words through **DB7/DOUTA**, with 128 SCLK cycles. Only V1/V2 are the two enabled EMG channels. Swap known V1/V2 voltages to verify identity; V3–V8 remain at the defined unused levels. | 3, 5 |
| Startup contains discarded SPI transactions. | Separate RESET-time reads from measured conversions: one per ADC configuration, normally one after diagnostic initialization and two before the first recording session after boot. They have no measurement CONVST and contribute no saved EMG sample. | 3, 7 |
| The virtual GPIO trace did not qualify physical idle-clock behavior. | Retain SPI mode 2: idle high and sample on falling edges. Measure SCLK at CS assertion on the real module, including after startup. Do not change clock polarity to imitate the simulator's idle-level limitation. | 3 |
| The analog path is unity gain; the midpoint is an unplugged-input bias. | Expect `RAW volts = signed code × 5 / 32768`, `input_scale=1` and `input_midpoint_mv=0`. Check the unplugged port near 1.5 V separately. Do not subtract 1.5 V twice or label ADC volts as input-referred muscle microvolts. | 4, 7 |
| Foot and shank begin acquisition at different times. | Check both CS identities and both INT1 wires. Keep their original timestamps and independent counters; unequal startup counts are possible. Do not align rows by their row number. | 6, 7 |
| A FIFO read can contain samples that arrived during that read. | Use the updated converter. Retain `read_start_us`, `read_end_us`, the IRQ anchor and the raw sensor counter. A sample after read start but before read end is not automatically a fault. Reconstructed host times remain estimates. | 6, 7 |
| A Wi-Fi preview lost one EMG record while the corresponding saved file retained it. | Audit the original SD file and laptop archive separately. A visible wireless gap must remain visible, but it does not establish SD loss. Conversely, a plausible preview cannot certify the saved file. | 7, 8 |
| A filename or decoded END can exist despite a final storage error. | Wait for recording to stop, retain the status/error indication, and convert the original file. Check CRC32, counters, timestamp quality, END and the stop reason together. Investigate sync/close errors even when END decodes. | 7–9 |

## Stage 3: connect the analyzer precisely

Use short high-impedance probes with a nearby common ground. The analyzer must accept 3.3 V logic. Connect only after the module's 5 V supply, 3.3 V VIO, serial-mode strap, internal reference and output levels pass [module qualification](module-qualification.md). Bare-chip pins and photographed carrier headers are different references.

| Signal | ESP32-S3 contact | Module / breadboard endpoint | Expected behavior |
|---|---|---|---|
| CONVST | J1.17 / GPIO11 | DIST1 a29 → b29/CVA and c29/CVB | One common rising trigger; 125 µs nominal period. The firmware delays 1 µs high; actual GPIO pulse width requires measurement and must meet the chip's ≥25 ns minimum. |
| BUSY | J1.12 / GPIO8 | ADC CN1 **BUSY** | Asserts after an accepted trigger; with oversampling off the AD7606 conversion is specified at 3.45–4.2 µs. Read only after it falls. The firmware's 80 µs wait is an error deadline, not acceptable normal conversion time. |
| CS | J1.16 / GPIO10 | DIST1 b28 → c28 / ADC CN1 **CS** | Active-low window containing 128 clocks for each measured frame. |
| SCLK | J1.18 / GPIO12 | ADC CN1 **RD** | 8 MHz, SPI mode 2. Verify physical idle high, sample edge and setup/hold. The clocked part of a 128-bit read is 16 µs. |
| DOUTA | J1.19 / GPIO13 | ADC CN1 **DB7** | Eight signed words in V1→V8 order, MSB first. DB8/DOUTB is not a second MISO lead in this build. |
| RESET | J1.15 / GPIO9 | ADC CN1 **RST** | Active high. Discard RESET-time reads before counting measurement frames. |

`ADC_DRDY` remains a shared firmware/net name for GPIO8; **on this AD7606 build the terminal is BUSY**, not a separate DRDY output. There is no external ADC clock module to add.

Use calibrated positive DC sources at V1/V2 before adding the analog boards. At ±5 V range, 1.000 V and 2.000 V give ideal codes 6554 and 13107. Use the actual meter reading in the calculation. The project integration screen is ±65 codes plus the measured source/meter uncertainty; it is not a precision calibration or datasheet accuracy claim. Swap the sources, then restore the documented ground/bias arrangement. Once BB1/BB2 are connected, use only the safe analog-stage stimulus range in the [synthetic-input procedure](synthetic-input-tests.md).

Retain the physical rate gate: **8 kHz ±0.1% averaged over 60 seconds**, and individual trigger intervals within the existing ±1% project screen. The virtual timing assessor uses its own simulator tolerance; it does not relax these lab gates. Diagnostics acquire in approximately one-second windows and stop triggers while printing. Exclude those intentional gaps from within-window rate measurements; use the recording image for continuous tests.

## Stage 6: keep the two motion streams identifiable

For the selected MIKROE-4237 carriers, set JP2–JP4 to SPI positions 1–2 and use the documented 3.3 V supply. Shared MOSI is **GPIO4**, MISO **GPIO5**, and SCLK **GPIO6**. Foot CS/INT1 use **GPIO7/16**; shank CS/INT1 use **GPIO15/17**. These assignments come from this ICM build, not an MPU-6050 address-selection diagram.

The firmware configures WHO_AM_I `0x47`, 200 Hz, ±16 g, ±2000 °/s, active-high INT1 pulses, and a standard 16-byte FIFO packet with a timestamp counter set to its 1 µs mode; on the ICM-42688 each tick lasts 32/30 µs, which firmware 1.8 applies. Check each carrier separately, then both together. In a recording, retained 16-bit sensor counters wrap every 65,536 ticks, about 69.9 ms. Normal wrap handling is different from an ambiguous long gap. Confirm FIFO order, sample counters and axis signs as well as interrupt activity.

The `FLAG_TIMING_UNCERTAIN` bit (`2`) marks reconstructed host times as estimates; it is expected on these ICM records. A gap bit, invalid sample, FIFO overflow, missing interrupt or rejected timestamp requires investigation. Foot/shank start offsets and filter delays need physical characterization before a study depends on accurate inter-sensor alignment.

## Stages 7 and 8: check the data you will actually analyze

Use `breadboard-sd-only-2ch` first, then `breadboard-record-2ch` for Wi-Fi. Both use SDMMC **CMD GPIO47, CLK GPIO39, D0 GPIO40** on Adafruit 4682. The PCB image uses CMD GPIO38 and is not interchangeable. Do not replace these connections with a generic SPI microSD diagram.

Copy the original SD file to the laptop, keep an untouched copy, and run from this variant's folder:

```sh
python3 host/convert.py trial.afolog --out trial-converted --no-plots
```

This CSV/JSON command needs only Python. For optional plots, install `host/requirements.txt` in a virtual environment and omit `--no-plots`. The [laptop setup guide](laptop-setup.html) includes a frozen synthetic recording, dependency instructions and a one-command package check.

Check `metadata.json`, `quality.json`, `emg.csv`, `foot.csv`, `shank.csv` and `status.csv`. Metadata must identify AD7606, two enabled inputs, ICM-42688-P, the breadboard hardware and the current firmware. Only EMG1/2 are measurements. AD7606 has no sensor-frame CRC/status word; blank ADC-specific columns are intentional. **Container CRC32 must still pass.** Preserve timestamp-estimate flags and both IMU read times.

For a normal manual stop, investigate any counter gap, invalid row, storage/queue error, missing END or unexpected stop reason. For an intentional interrupted-power test, the recovery report must identify the truncated tail/missing END; it must not present recovered partial data as a complete successful trial. Use `--recover` only for that explicitly labeled recovery exercise.

Then receive Wi-Fi while SD continues, disconnect/reconnect wireless and compare the two archives. Use the [saved-data guide](data-interpretation.html) for units, flags and [real simulated example files](../simulations/recording-interpretation/recording-examples.zip). Simulated examples illustrate interpretation; they do not fill any laboratory result cell.

## Remaining physical checks

Supply startup/ripple, received-module straps and logic levels, physical SPI edges, analog noise/crosstalk, actual SDMMC behavior, RF reception and battery runtime remain unmeasured. No compact PCB order is recommended until the relevant lab gates and final design review pass. The bench setup validates circuit blocks; the final board still needs its own layout-dependent checks.

Manufacturer references: [AD7606 Rev. G](https://www.analog.com/media/en/technical-documentation/data-sheets/AD7606_7606-6_7606-4.pdf), especially Tables 2–3 and Serial Interface; [ICM-42688-P manufacturer page](https://www.invensense.tdk.com/en-us/products/6-axis/icm-42688-p). Read the selected carrier's included schematic/header evidence before wiring.
