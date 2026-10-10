# Checks on the downloaded breadboard kit

**AD7606 · two EMG inputs · ICM-42688-P.** The current [lab kit](../breadboard/breadboard-lab-kit.zip) was extracted into a temporary folder outside the project. These checks run its actual laptop files, rather than relying on imports or assets available only in the repository. See the [machine-readable receipt](kit-validation.json) for the tested archive hash and results. No physical recorder was connected.

## Two handoff gaps corrected

The earlier kit omitted `simulations/run_acquisition.py`, which its reader regression tests import. That source-only synthetic fixture is now included, with a [test runner](../host/run_tests.py) that sets the local import paths. Legacy four-channel reader tests remain; this fixed-two hardware still rejects four-channel firmware.

The earlier start command requested plots without explaining their Matplotlib dependency. The [laptop setup guide](laptop-setup.html) now gives a Python-only `--no-plots` route, an optional plotting environment, Windows command equivalents, new-output-folder rules and the meaning of converter exit codes. Converter behavior and the recording format are unchanged.

The kit also includes a frozen [synthetic recording](../breadboard/recording-example.afolog), its [provenance receipt](../breadboard/recording-example.json) and an [integrity/data check](../host/check_package.py). Its bytes match the previously preserved Wokwi capture. It is not a new hardware measurement.

## Results and what they establish

| Check | Observed result | Scope |
|---|---|---|
| Packaged host suite in a Python environment without Matplotlib | All 46 tests passed, including corruption/recovery, enabled channels, legacy decoding, wireless gaps, the 1,400-byte metadata limit, record-queue duration, absence of a compiled Wi-Fi password and the IMU clock screen | Reader/telemetry code and the fixed-two circuit/firmware contract; the C guard test uses a host compiler |
| Frozen saved-file conversion | 10,041 EMG frames, 263 foot samples, 252 shank samples, one status and one END; no detected saved-file gap | Correct decoding of this captured synthetic session |
| Units and timing flags | Exactly two EMG columns; signed code × 5 / 32768 voltage scaling; all 515 IMU timing-estimate flags preserved | Interpretation; no measured calibration or timing alignment |
| Optional plot environment | Checked on the previous (firmware 1.6) archive: the documented dependency installation completed and default conversion produced PNG and SVG plots. Not repeated for the 1.7 archive; see the receipt | Python plotting workflow on this macOS/Python environment |
| Packaged receiver with captured UDP input | 1,123 packets replayed over loopback; 10,557 archived records preserved byte for byte | Laptop socket, API and archive path; no radio or ESP32 Wi-Fi execution |
| Saved file versus wireless archive | Wireless EMG sequence 5330 remained missing; saved file retained it. Wireless conversion returned code 2 and reported the gap | Separate quality reporting; missing wireless data was not filled or presented as saved-file loss |
| Corrupt and duplicate UDP packets | Both rejected without adding measurements | Receiver fault handling |
| Modified example file | Package check rejected the changed file | Manifest integrity checking |
| Extracted viewer with external assets blocked | Checked on the previous archive with no failed asset requests or console errors. The 1.7 archive changes only guide text in the viewer; the browser check was not repeated | Local asset closure and UI behavior; geometry and wire bends remain illustrative |

The example's host-derived EMG rate is about 7,983.86 Hz in Wokwi. Its saved-file integrity result does not certify the physical **8 kHz ±0.1%** gate. The simulator's schedule, substitute storage and injected battery reading do not establish real sample-rate accuracy, SDMMC behavior or battery runtime.

## Repeat the checks

For the extracted kit:

```sh
python3 host/check_package.py --out package-check.json
python3 host/run_tests.py
python3 host/convert.py breadboard/recording-example.afolog --out example-csv --no-plots
```

The test suite needs a C compiler named `cc` for one firmware contract test. CSV conversion and the package check need only Python. Preserve the kit manifest and your receipts; use new result paths rather than overwriting earlier evidence.

For the repository-level extraction and captured-UDP replay, run [the download verifier](../design/verify_breadboard_download.py) from this variant's folder:

```sh
python3 design/verify_breadboard_download.py --python /path/to/test-python --out /path/to/new-results
```

Add `--plot-python /path/to/plot-environment/bin/python` to check plots as well. This verifier uses the preserved UDP capture in the full repository; that historical capture is not duplicated into the small lab kit. The [receipt](kit-validation.json) records whether plotting ran and whether Matplotlib was present in the CSV-test environment. Browser checks were performed separately against a loopback server restricted to local resources.

## What still needs a lab

Received-module straps, output logic levels, reference voltage, power startup/ripple, analog noise/crosstalk, physical SPI edges, actual SDMMC endurance, radio reception, temperature and battery runtime remain unmeasured. The six laboratory firmware profiles (source set 1.7) have not been flashed to an assembled recorder. All 30 rows of the [bench checklist](bench-checklist.csv) remain **NOT TESTED**. Continue with the [lab sequence](lab-quickstart.html) when hardware and instruments are available; these software checks do not recommend a PCB order.
