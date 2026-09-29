# Project lead: Muttakin Rahman

Start with [the guided build](viewer/build.html). The [source and licence notices](THIRD_PARTY_NOTICES.md) distinguish project material from third-party assets.

> Current assembly entrypoint: [complete build guide](docs/build-guide.html), [module qualification](docs/module-qualification.md), and [current validation](docs/validation-report.md). Historical reports and stage overview drawings are retained for traceability.

# AD7606 · Two EMG channels — ICM-42688-P

[Open the assembly viewer](viewer/index.html) · [Build guide](docs/staged-build-guide.md) · [Wiring guide](docs/breadboard-assembly.md)

This focused revision corrects diagnostics and metadata for the fixed two-input ICM build. Other variants are unchanged.

Start with the [circuit audit and verification limits](docs/circuit-audit.md), [short lab sequence](docs/lab-quickstart.md), and [Wokwi package](simulations/wokwi/README.md). Wokwi system execution remains pending; no physical validation is claimed.

Serve this folder over HTTP; opening the viewer directly as a local HTML file will block asset fetches in most browsers. Standard filenames such as CMakeLists.txt, main.c, index.html and KiCad project members are retained for tool compatibility.

All hardware remains an engineering prototype pending physical validation. Module pin positions and outstanding wiring gates are documented; no board order is implied.
