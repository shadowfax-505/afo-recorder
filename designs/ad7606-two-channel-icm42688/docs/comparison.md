# Three separate versions

| Package | Physical EMG inputs | Active channels | ADC |
|---|---:|---:|---|
| afo-ads131m04 | 4 | 2 or 4 | ADS131M04, 24-bit words |
| afo-ad7606 | 4 | 2 or 4 | AD7606, 16-bit words |
| **afo-ad7606-two** | **2** | **2 only** | **AD7606, 16-bit words** |

This package removes EMG3/EMG4, their protection and RC components: 18 parts removed, 106 component entries retained. It keeps the 75 × 50 mm, four-layer outline and U3/U4 quad amplifier packages. Unused amplifier halves are terminated locally. It is not a board-area optimization or an expandable four-input PCB.

All retain two remote ready-made IMUs, 8 kHz EMG frames, SD and best-effort Wi-Fi. The AD7606 still converts eight inputs and the driver reads eight words, but V3–V8 are grounded and only EMG1/EMG2 are exported. No AD7606 sensor CRC exists; file/packet CRC does not prove correct ADC bus data.

The lab build uses RoboticsBD RBD-3184, subject to actual header/VIO/serial-mode verification. The ADS option depends on procuring its evaluation/breakout board. Both AD versions require regulated 5 V for the converter and 3.3 V logic. ADC word width is not effective resolution; noise, timing, wireless coexistence and runtime remain physical tests.

Existing packages are preserved. Do not interchange binaries solely because connector labels look similar. Review each hardware identity and firmware manifest.
