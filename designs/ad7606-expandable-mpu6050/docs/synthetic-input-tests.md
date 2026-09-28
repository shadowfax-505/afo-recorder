# Synthetic input connections

For stages 4–5 leave MyoWare completely disconnected. Use the following RAW-wire substitutions; no sensor power lead is needed. Common-ground the signal generator with the recorder before enabling its output. Set 1.5 V DC offset and 100 mVpp sine initially, confirming the actual generator output under its configured load. Never apply ±5 V to the 3 V analog buffers.

- myo1: generator signal connects to **DIST1:b34**, replacing wire wire-133; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo2: generator signal connects to **DIST1:b37**, replacing wire wire-139; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo3: generator signal connects to **DIST1:b40**, replacing wire wire-145; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.
- myo4: generator signal connects to **DIST1:b43**, replacing wire wire-151; generator return goes to a verified free GND strip hole. Do not add a second lead into an occupied hole.

For stage 3 disconnect conditioned AIN leads at the ADC and apply known DC test levels directly to its verified input terminal and return. ADS tests must respect differential and common-mode limits: keep AINN at midpoint, start AINP at midpoint and use small differential offsets. AD7606 tests use input relative to ground. Reconnect the original wires with all power off before proceeding. See staged-build-guide.md for code and timing acceptance targets.

myo1 generator return: replace sensor ground wire wire-050 at **DIST1:c11**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo2 generator return: replace sensor ground wire wire-053 at **DIST1:c12**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo3 generator return: replace sensor ground wire wire-056 at **DIST1:c13**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.

myo4 generator return: replace sensor ground wire wire-059 at **DIST1:c14**. Leave the sensor end unplugged. This reuses its assigned hole rather than sharing a occupied hole.
