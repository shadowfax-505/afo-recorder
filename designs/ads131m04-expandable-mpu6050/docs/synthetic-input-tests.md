# Synthetic input connections

For stages 4–5 leave MyoWare completely disconnected. Use the following RAW-wire substitutions; no sensor power lead is needed. Common-ground the signal generator with the recorder before enabling its output. Set 1.5 V DC offset and 100 mVpp sine initially, confirming the actual generator output under its configured load. Never apply ±5 V to the 3 V analog buffers.

- myo1: generator signal connects to **DIST1:b25**, replacing wire wire-098; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo2: generator signal connects to **DIST1:b29**, replacing wire wire-106; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo3: generator signal connects to **DIST1:b33**, replacing wire wire-114; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo4: generator signal connects to **DIST1:b37**, replacing wire wire-122; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.

For stage 3 disconnect conditioned AIN leads at the ADC and apply known DC test levels directly to its verified input terminal and return. ADS tests must respect differential and common-mode limits: keep AINN at midpoint, start AINP at midpoint and use small differential offsets. AD7606 tests use input relative to ground. Reconnect the original wires with all power off before proceeding. See staged-build-guide.md for code and timing acceptance targets.

myo1 generator return: replace sensor ground wire wire-031 at **DIST1:e7**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo2 generator return: replace sensor ground wire wire-033 at **DIST1:d8**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo3 generator return: replace sensor ground wire wire-035 at **DIST1:c9**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo4 generator return: replace sensor ground wire wire-037 at **DIST1:e9**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.
