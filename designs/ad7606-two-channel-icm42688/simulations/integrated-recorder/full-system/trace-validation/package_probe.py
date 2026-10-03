"""Package the optional pin-observer scene with its unchanged recorder image."""
from pathlib import Path
import hashlib
import json
import zipfile

from assess_probe import assess

P = Path(__file__).resolve().parent


def package():
    result = assess(P / 'probe-run')
    assert result['pass'], result['pin_checks']['errors']
    base = P.parent
    root = P.parents[3]
    files = {}
    # Keep the original full-system drawing/manifest together. The optional
    # observer drawing lives in its named subfolder and is selected explicitly.
    for name in ['README.md', 'NOTICE.md', 'esp32-bin-file.ino', 'diagram.json', 'manifest.json']:
        files[f'integrated-recorder/full-system/{name}'] = base / name
    for path in sorted(base.glob('*.chip.*')):
        files[f'integrated-recorder/full-system/{path.name}'] = path
    names = ['README.md', 'diagram.json', 'probe.chip.c', 'probe.chip.json', 'probe-manifest.json',
             'observations.json', 'instrument-tests.json', 'prepare_probe.py', 'assess_probe.py',
             'export_edges.py', 'test_probe.py', 'probe_fixture.c', 'probe_test_api.h']
    for name in names:
        files[f'integrated-recorder/full-system/trace-validation/{name}'] = P / name
    capture = ['result.json', 'capture-origin.json', 'chips-console.txt', 'serial.txt', 'tested-build.json',
               'observed-diagram-before-run.json', 'diagram.json', 'probe-manifest.json',
               'sampled-edges.csv', 'sampled-edges.vcd', 'edge-exports.json', 'adc-timing.png', 'adc-timing.svg']
    for name in capture:
        files[f'integrated-recorder/full-system/trace-validation/probe-run/{name}'] = P / 'probe-run' / name
    for name in ['merged.bin', 'manifest.json']:
        files[f'integrated-recorder/firmware/{name}'] = base.parent / 'firmware' / name
    for path in sorted((root / 'licenses/esp-idf').rglob('*')):
        if path.is_file(): files[path.relative_to(root).as_posix()] = path
    out = P / 'digital-timing-wokwi.zip'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        for name, path in files.items(): assert archive.read(name) == path.read_bytes(), name
    report = {'file': out.name, 'bytes': out.stat().st_size,
              'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'simulation_only': True,
              'hardware_measured': False, 'research_ready': False,
              'instrumented_scene_parts': 38, 'instrumented_scene_connections': 89,
              'saved_public_scene_modified': False, 'executed_web_probe_supplied_as_c_source': True,
              'local_cli_probe_wasm_included': False, 'full_session_vcd_qualified': False,
              'sha256_contents': {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in sorted(files.items())}}
    (P / 'download.json').write_text(json.dumps(report, indent=2) + '\n')
    (P / 'digital-timing-wokwi.zip.sha256').write_text(f"{report['sha256']}  {out.name}\n")
    return report


if __name__ == '__main__':
    result = package()
    print(json.dumps({k: result[k] for k in ['file', 'bytes', 'sha256']}))
