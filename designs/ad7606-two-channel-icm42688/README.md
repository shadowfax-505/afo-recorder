# Project lead: Muttakin Rahman

Start with [the guided build](viewer/build.html). The [source and licence notices](THIRD_PARTY_NOTICES.md) distinguish project material from third-party assets.

> Current assembly entrypoint: [complete build guide](docs/build-guide.html), [module qualification](docs/module-qualification.md), and [current validation](docs/validation-report.md). Historical reports and stage overview drawings are retained for traceability.

# AD7606 · Two EMG channels — ICM-42688-P

[Open the assembly viewer](viewer/index.html) · [Build guide](docs/staged-build-guide.md) · [Wiring guide](docs/breadboard-assembly.md)

This focused revision corrects diagnostics and metadata for the fixed two-input ICM build. Other variants are unchanged.

Start with the [circuit audit and verification limits](docs/circuit-audit.md), [short lab sequence](docs/lab-quickstart.md), and [Wokwi package](simulations/wokwi/README.md). Seven actual-firmware Wokwi scenarios pass; [execution results](docs/virtual-verification.md) state the capture/model limits. Physical validation remains outstanding.

Serve this folder over HTTP; opening the viewer directly as a local HTML file will block asset fetches in most browsers. Standard filenames such as CMakeLists.txt, main.c, index.html and KiCad project members are retained for tool compatibility.

All hardware remains an engineering prototype pending physical validation. Module pin positions and outstanding wiring gates are documented; no board order is implied.

Additional checks: [production ADC driver host tests](simulations/driver-tests/README.md) and [simulation evidence safeguards](simulations/wokwi/README.md#evidence-safeguards). The [Wokwi report](docs/virtual-verification.md) separately records actual ESP32 simulator execution.

Recording firmware **ad7606-2ch-1.4** adds safe task ownership through shutdown and a final storage verdict before wireless END. [Recording verification](docs/recording-verification.html) documents 38 native control cases, RTOS lifecycle evidence, recovery limits and stop indications. Three recording images were rebuilt; four diagnostic images retain their prior tested binaries. No physical measurements or PCB order are implied.
