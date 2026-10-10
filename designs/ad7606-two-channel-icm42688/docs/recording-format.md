# Recording compatibility

Files retain AFOLOG1 headers and64-byte CRC-protected records. Metadata schema1 is the legacy multiplexed12-bit recorder, schema2 is ADS131M04, schema3 is AD7606. Record kind6 carries ADS frames; kind7 carries AD7606 frames. The shared40-byte EMG payload contains four signed32-bit code slots,16-bit ADC status,16-bit ADC CRC, read duration, elapsed slots, enabled mask and read-start timestamp. Only the enabled2/4 slots are valid; disabled slots are zero and excluded from output.

For schema3, ADC status and ADC CRC must both be zero because AD7606 has no sensor-frame CRC. The file/packet checksum detects damaged stored/transmitted records, not every error between ADC and ESP32. Signed16-bit bounds are enforced. The legacy field adc_reference_mv=5000 denotes nominal signed ADC full-scale, not the physical2.5 V reference pin. Voltage=code×5/32768. The analog path has unity gain; its offset remains in the stored input waveform.

Schema2 uses adc_reference_mv=1200, voltage=code×1.2/8388608, gain0.5 around the1.5 V midpoint. Metadata records uncalibrated/nominal scaling; do not relabel it calibrated without measurement. ADC filtering and timestamp events differ between variants. Host timestamps are estimates requiring bench timing characterization; simultaneous conversion does not remove filter latency.

The converter and laptop receiver accept all three schemas. Original binary readings are retained; synthetic examples explicitly identify synthetic=true. Generated recovery reports expose losses rather than interpolating missing muscle data.

This hardware is `AD7606_TWO_FIXED`: exactly two enabled slots, mask 0x03, EMG1/EMG2. Slots 2 and 3 remain zero for binary compatibility. The shared reader still supports older four-channel files; this does not enable extra inputs on this PCB.

## Current fixed-two timing metadata

The 1.6 and current 1.7 recorders retain `input_scale=1` and `input_midpoint_mv=0` so conversion reconstructs the RAW connector voltage. `unplugged_input_bias_mv=1500` separately describes the circuit’s bias; it is not an additive voltage-reconstruction offset. `imu_time=fifo_delta_first_irq` identifies first-burst interrupt anchoring followed by sensor-counter increments. FIFO order, sensor counter, interrupt anchor and read timing remain available; estimates are flagged uncertain and are not calibrated timestamps.

Integrated simulator `.raw` captures retain the exact production bytes, whose metadata originally says `synthetic=false`. They are simulation evidence, not human recordings. Their companion `.afolog` files explicitly set `synthetic=true`; see the [integrated evidence report](integrated-verification.html) before using a fixture.
