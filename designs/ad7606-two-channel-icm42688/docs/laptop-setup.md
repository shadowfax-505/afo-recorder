# Start the downloaded lab kit

**AD7606 · two EMG inputs · ICM-42688-P.** Extract the [breadboard lab kit](../breadboard/breadboard-lab-kit.zip) and open a terminal in its folder, beside `START-HERE.md`. The viewer, CSV converter and Wi-Fi receiver work with local files. Plotting is an optional Python dependency. The [download-check report](download-checks.html) records the standalone tests and their limits.

## Open the build instructions

```sh
python3 -m http.server 8769 --bind 127.0.0.1
```

Open [the local build view](http://127.0.0.1:8769/viewer/build.html?stage=1). If another server already uses 8769, choose an unused port such as 8770 and use that port in the address. Keep the terminal open while viewing; Ctrl+C stops the server. Serve only the extracted kit, not your home folder. Assembly assets and the stage instructions are local. Links to historical evidence, manufacturing files and the main project use the published website and need an internet connection.

## Try CSV conversion before building

The kit includes `breadboard/recording-example.afolog`, copied byte for byte from the previously captured synthetic Wokwi recording. Its [provenance receipt](../breadboard/recording-example.json) identifies the source and hash. It contains 10,041 EMG frames, 263 foot samples, 252 shank samples, one status record and one END. The foot and shank started at different times. This is a software example, not a measurement from a person or an assembled recorder.

No extra Python packages are needed for CSV and JSON output:

```sh
python3 host/convert.py breadboard/recording-example.afolog --out example-csv --no-plots
python3 host/check_package.py
```

Use a new output directory each time. The converter refuses to overwrite an existing result. Open `example-csv/emg.csv`, `foot.csv` and `shank.csv` in your analysis software, and keep `metadata.json` and `quality.json` with them. Only EMG1/2 appear. ADC voltage and estimated MyoWare RAW voltage are in volts; they are not input-referred muscle microvolts. The 515 motion samples retain timing-estimate flags. See [saved-data interpretation](data-interpretation.html) for units, counters and timestamp alignment.

For your future SD file, keep an untouched copy and replace the example path:

```sh
python3 host/convert.py trial.afolog --out trial-csv --no-plots
```

Exit code 0 means the converter's loss/signal checks passed; code 2 means output contains reported quality problems. Code 1 means conversion or a dependency failed. A clean conversion is not a calibration or electrical-safety certificate.

## Add plots when needed

Create a Python environment and install the plotting dependency listed in the kit:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r host/requirements.txt
.venv/bin/python host/convert.py breadboard/recording-example.afolog --out example-plots
```

On Windows, use `py` for environment creation and `.venv\Scripts\python.exe` for the last two commands. The default conversion command creates `signals.png` and `signals.svg` in addition to CSV/JSON. Without Matplotlib, use `--no-plots`. If a previous default command reported missing Matplotlib after creating CSV files, retain those files and their quality report, install the dependency, and rerun into a **new** output folder.

## Run the supplied checks

```sh
python3 host/check_package.py --out package-check.json
python3 host/run_tests.py
```

The first command verifies the manifest hashes and frozen example's two-channel scaling, row counts and motion timing flags. The second runs the packaged regression tests, including legacy-file support and synthetic fault cases. It needs a C compiler named `cc` for the firmware channel-count guard; CSV conversion and live reception do not. No ESP-IDF or Wokwi installation is needed for these laptop checks. They do not execute a physical ESP32 or establish analog, storage, radio or runtime performance.

## Receive Wi-Fi after the storage stage passes

Keep the original SD recording as the primary archive. Connect the laptop to the recorder's access point, then run:

```sh
python3 host/live_receiver.py --device 192.168.4.1 --out trial-wifi
```

The local live page opens at port 8766. Ctrl+C stops reception and closes the laptop archive. Use a new capture folder for each run. Convert the captured `.afolog` file with `--no-plots` or your plotting environment, and compare its quality report with the original SD file. A wireless gap is not automatically an SD gap. The downloaded example verifies interpretation only; it cannot test your laptop's radio or the received modules.

## Continue to physical stages

Use the [short lab sequence](lab-quickstart.html), [exact wire tables](build-guide.html), [probe contacts](../breadboard/probe-connections.csv) and [blank checklist](bench-checklist.csv). All physical outcomes remain **NOT TESTED**. The six included firmware profiles are laboratory builds, cross-compiled and not flashed to an assembled recorder. The kit excludes simulation-only images and the compact-PCB recording image. Flash all three files at the offsets in the chosen profile's manifest.
