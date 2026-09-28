# Start here

The recorder captures MyoWare 2.0 RAW signals and foot/shank motion, saves original readings to microSD and sends a best-effort Wi-Fi copy to a laptop. It is an acquisition research prototype, not an AFO controller or a clinically validated device.

Choose one complete package from the project index. Use matching hardware, firmware and wiring documents; do not combine the SPI wiring from an ICM package with the I²C MPU firmware.

| Choice | Use |
|---|---|
| AD7606 two-channel | Exactly two MyoWare inputs; four-channel firmware is intentionally rejected |
| AD7606 expandable | Four populated inputs; enable two or four at 8 kHz per channel |
| ADS131M04 expandable | Four populated inputs; enable two or four at 8 kHz per channel; lab ADC carrier availability remains a dependency |
| ICM-42688-P | Original SPI motion-sensor design; exact carrier procurement remains open |
| GY-521/MPU-6050 | New I²C alternative using the locally linked module; timing reconstructed from interrupts and FIFO order |

Both IMU families target 200 Hz for foot and shank. A sensor timestamp is not automatically synchronized to EMG; both need calibration and timing characterization.

Read [system architecture](system-architecture.md), then [lab build guide](lab-build-guide.md), [recording and analysis](recording-and-analysis.md), and [validation status](validation-status.md). Begin with synthetic electrical signals; participant recordings require the institutional and electrical-safety approvals described in each package.

To view locally from the workspace: `python3 -m http.server 8769 --bind 127.0.0.1 --directory outputs`, then open `/afo-recorder-project/` on that server. Do not open the 3D viewer with a file:// URL.

Read [SD card wiring](sd-card-wiring.md) before stage 7. The current breadboard profiles use GPIO47 for CMD.

For source builds, see [firmware build guide](firmware-build-guide.md).

Read [current wiring status](wiring-status.md) before attempting the new connections.
