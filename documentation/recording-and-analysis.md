# Recording and analysis

## Before recording

Select the exact package, hardware role and channel count. Firmware build manifests contain flash offsets, hashes and configuration. Recorder builds require working SD, battery sensing and USB inhibition; diagnostic builds bypass unrelated stages for bench tests only. Use the updated breadboard build with SD CMD on GPIO47; PCB builds use GPIO38. Follow sd-card-wiring.md before stage 7.

Use pseudonymous trial identifiers and record sensor location, electrode placement, orientation, calibration state and any measured timing corrections. Keep the original binary file unchanged.

## File conversion

Create a Python environment and install `host/requirements.txt` from the selected package. Run:

```sh
python host/convert.py trial.afolog --out exported-trial
```

Outputs include EMG and IMU CSV files, metadata, quality reports and signal plots. `--recover` salvages valid records from interrupted/corrupt recordings and explicitly reports damage; it does not fill missing samples. Exit code 2 means quality checks detected an issue. Inspect the report rather than treating every nonzero result as a software crash.

For MPU synthetic examples:

```sh
python host/generate_mpu_example.py demo.afolog --channels 2 --fault none
python host/convert.py demo.afolog --out demo-export
```

Expandable versions also accept four channels. Synthetic examples are labeled and never constitute hardware, clinical or battery evidence. `generate_example.py` remains a legacy-format regression fixture.

## Live reception

Use `python host/live_receiver.py --help` for the package's receiver options. Join the recorder Wi-Fi and start the laptop receiver, then begin the device recording. MicroSD remains the primary copy. Packet gaps, invalid packets and sensor sequence gaps must remain visible; wireless reception is best effort.

MPU records use types 8 and 9 for foot and shank. Data types 2 and 3 retain ICM meaning. The MPU converter leaves sensor timestamp/temperature fields blank and retains FIFO batch index/count. All MPU time estimates are flagged uncertain; apparent millisecond EMG-motion relationships require lab timing validation and filter-delay characterization.
