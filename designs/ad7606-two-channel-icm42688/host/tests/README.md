# Run the laptop tests

From the extracted kit or this variant's folder:

```sh
python3 host/run_tests.py
```

The runner sets the local import paths. No plotting package, ESP-IDF, Wokwi account
or Python path configuration is needed. A C compiler available as `cc` is required
for the test that rejects four-channel firmware on the fixed-two board.

The tests cover legacy recordings, AD7606 signed scaling, disabled channels,
container and wireless CRCs, corruption/recovery, channel identity, missing data
and the fixed-two circuit contract. `simulations/run_acquisition.py` is a synthetic
test fixture included in the kit; it does not run the ESP32 or emulate physical
power, analog noise, radio behavior or battery capacity. The shared reader's
legacy four-channel tests do not enable four inputs on this hardware.

Run `python3 host/check_package.py` to verify the extracted files and decode the
included frozen Wokwi example. This is a separate check, not a laboratory result.
