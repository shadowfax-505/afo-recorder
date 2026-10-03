# Recording examples and independent byte audit

Muttakin Rahman · AD7606 / two-channel / ICM-42688-P · 3 October 2026

These are data captured from the actual ESP-IDF recorder image executing in Wokwi. They are synthetic inputs, not human recordings or measurements from an assembled recorder.

Two runs are checked: the complete-scene input-only pin-probe run with known 1 V / 2 V ADC codes, and case 14 of the earlier 18-case web matrix with precomputed ngspice voltages. Both use the same frozen v1.6 image. The latter retains its smaller protocol-fixture diagram; it is not relabeled as a complete-scene execution.

`verify_saved_data.py` independently parses the original binary format, checks CRCs and compares every CSV value and saved/live record. It uses the Python standard library and does not import the converter. `test_saved_data.py` rejects eleven damaged-data examples without altering the original evidence. `analyze_example.py` makes named, relative-time tables with no filtering, resampling or gap filling. `plot_saved_data.py` plots the existing waveform CSV using Matplotlib.

From the complete repository:

```sh
python3 designs/ad7606-two-channel-icm42688/simulations/recording-interpretation/verify_saved_data.py
python3 designs/ad7606-two-channel-icm42688/simulations/recording-interpretation/test_saved_data.py
```

From the extracted example download:

```sh
python3 verify_saved_data.py --examples examples --output checked-results.json
python3 analyze_example.py examples/synthetic-waveform/converted my-analysis
```

Open `examples/synthetic-waveform/analysis/muscle.csv` for EMG1/EMG2 volts and seconds relative to the first trigger. Foot/shank analysis tables preserve the estimated timing, quality flags and negative startup times. Keep metadata and quality reports alongside every table. The raw ADC voltages are not input-referred muscle microvolts or normalized muscle activation.

The original firmware-produced header says `synthetic=false` because the production image does not automatically detect the simulator. Its retained `recorder-output.raw` must always be interpreted with the capture's sidecars/manifests. The tagged `.afolog` changes only simulation provenance in the header; its measurement records are identical. Both hashes are in `results.json`.

The timing scene uses a PSRAM block medium and internal UDP subscriber. Actual SDMMC, the card, radio and analog/power physics remain substituted. The underlying ADC and IMU models are project-authored behaviors. An official simulator platform does not establish physical correctness of these models. No hardware measurement, calibration, clinical acceptance or research-ready data is claimed.

The download includes `data-guide.html` with its plot for offline reading. Its links to the broader project evidence open the website. The online report is [Read and interpret a saved recording](https://shadowfax-505.github.io/afo-recorder/designs/ad7606-two-channel-icm42688/docs/data-interpretation.html). `package_examples.py` builds and checks `recording-examples.zip`; `download.json` lists every included file hash.
