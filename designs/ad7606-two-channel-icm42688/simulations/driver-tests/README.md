# AD7606 driver logic checks

Run `python3 run.py` from this directory with a C11 compiler available (`CC` can select it). The test includes the production `firmware/main/adc_ad7606.c` directly; it does not maintain a second copy of the driver. The source SHA-256 is recorded in `results.json`.

Nine groups check no read before a conversion, 128-clock transfer configuration, signed channel order and disabled outputs, trigger timestamp retention, stuck/preexisting BUSY, unread conversions, late reads, SPI errors, restart and initialization error propagation. Tests inject the next conversion deadline during a SPI read and require an error rather than acceptance of that frame.

This is **host execution of C control logic with mocked peripherals**. Critical-section macros are no-ops in the shim. There is no real scheduler, concurrent core, ESP-IDF peripheral implementation, physical signal, or timing measurement. Passing these assertions does not resolve Wokwi's SPI contention or establish 8 kHz hardware performance.
