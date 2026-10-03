#!/usr/bin/env python3
"""Package the current breadboard instructions, viewer and laboratory profiles."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import zipfile

VARIANT = Path(__file__).resolve().parent.parent
REPO = VARIANT.parents[1]
SITE = 'https://shadowfax-505.github.io/afo-recorder/'
PROFILES = ['diagnostic-controller', 'diagnostic-adc', 'diagnostic-imu-one',
            'diagnostic-imu-two', 'breadboard-sd-only-2ch', 'breadboard-record-2ch']
ARCHIVE_ROOT = 'ad7606-two-channel-icm42688-breadboard'


def checksum(data):
    return hashlib.sha256(data).hexdigest()


def collect_files():
    files = {}
    for folder in ['breadboard', 'viewer', 'docs', 'host']:
        for path in (VARIANT / folder).rglob('*'):
            if (not path.is_file() or '__pycache__' in path.parts or path.suffix in ['.pyc', '.zip']
                    or path.name in ['breadboard-lab-kit.json', 'guidance-validation.json',
                                     'kit-validation.json']):
                continue
            files[path.relative_to(VARIANT).as_posix()] = path
    for name in ['CMakeLists.txt', 'sdkconfig.defaults']:
        files['firmware/' + name] = VARIANT / 'firmware' / name
    for path in (VARIANT / 'firmware/main').iterdir():
        if path.is_file():
            files[path.relative_to(VARIANT).as_posix()] = path
    for profile in PROFILES:
        for path in (VARIANT / 'firmware/builds' / profile).iterdir():
            if path.is_file():
                files[path.relative_to(VARIANT).as_posix()] = path
    for name in ['README.md', 'validation.json']:
        files['firmware/builds/' + name] = VARIANT / 'firmware/builds' / name
    for name in ['main.json', 'breadboard-gpio-map.json']:
        files['design/' + name] = VARIANT / 'design' / name
    # Reader regression tests import this source-only synthetic queue fixture.
    files['simulations/run_acquisition.py'] = VARIANT / 'simulations/run_acquisition.py'
    for name in ['README.md', 'THIRD_PARTY_NOTICES.md']:
        files[name] = VARIANT / name
    for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
        if (REPO / name).exists():
            files['project-' + name] = REPO / name
    return files


def package():
    files = collect_files()
    included = {path.resolve() for path in files.values()}
    content = {}
    rewritten_pages = []
    for name, path in files.items():
        data = path.read_bytes()
        if path.suffix == '.html':
            source = data.decode()

            def link(match):
                href = match[1]
                parts = urlsplit(href)
                if parts.scheme or parts.netloc or not parts.path:
                    return match[0]
                destination = (path.parent / parts.path).resolve()
                if destination in included:
                    return match[0]
                if destination.is_relative_to(REPO):
                    target = SITE + destination.relative_to(REPO).as_posix()
                    if parts.query:
                        target += '?' + parts.query
                    if parts.fragment:
                        target += '#' + parts.fragment
                    return 'href="' + target + '"'
                return match[0]

            source = re.sub(r'href="([^"]+)"', link, source)
            if source.encode() != data:
                rewritten_pages.append(name)
            data = source.encode()
        content[name] = data

    content['START-HERE.md'] = b'''# AD7606 two-channel breadboard lab kit

Project lead: Muttakin Rahman

Use this kit for exactly two MyoWare RAW inputs and two ICM-42688-P carriers.
Circuit routing remains revision 12; instructions apply the v1.6 simulation findings.
No physical measurement has been completed or certified.

1. Open a terminal in this extracted folder and run:
   python3 -m http.server 8769 --bind 127.0.0.1
2. Open http://127.0.0.1:8769/viewer/build.html?stage=1
   Read docs/breadboard-refinements.html and docs/lab-quickstart.html.
3. Work through the stages with power off between additions. Use the exact hole
   tables and breadboard/probe-connections.csv; fill docs/bench-checklist.csv with
   real readings and evidence. All supplied outcomes are NOT TESTED.
4. Flash one of the six included firmware/builds profiles, using all three files
   and the offsets from its manifest. Keep the actual application hash with the trial.
   Breadboard SDMMC is CMD GPIO47 / CLK GPIO39 / D0 GPIO40.
5. Convert an untouched SD copy with:
   python3 host/convert.py trial.afolog --out trial-converted --no-plots
   Audit the original SD file and laptop archive separately.

Before building hardware, try the included synthetic recording:
   python3 host/convert.py breadboard/recording-example.afolog --out example-csv --no-plots
   python3 host/check_package.py
   python3 host/run_tests.py
The test suite needs a C compiler named cc for one firmware contract check.
CSV conversion, file-integrity checks and Wi-Fi reception need only Python.
For optional plots, install host/requirements.txt in a Python virtual environment.
Read docs/laptop-setup.html for the commands, units and troubleshooting.

Included firmware uses source set ad7606-2ch-1.6 and ESP-IDF v5.4.2. It has been
cross-compiled, not flashed to an assembled recorder. The canonical validation
file describes seven compiled profiles; this archive intentionally includes only
the six breadboard profiles. The PCB recording binary and Wokwi simulation-only
images are excluded. Do not flash an instrumented simulator image to hardware.

The viewer uses local assets and an HTTP server. Offline guides and wire tables
are included. Evidence/manufacturing links outside this kit open the published
project; those links were rewritten in packaged HTML only. Complete KiCad and
historical simulation evidence remain in the main project repository.
The included run_acquisition.py is a source-only synthetic regression fixture.
The example is a frozen synthetic recording, not an assembled-recorder measurement.

Check the received AD7606 board's supplies, logic levels, internal reference and
serial straps BEFORE adding ESP32 signal leads. Follow module qualification.
Use synthetic signals only with instruments/USB attached; no person connected.
Read the included source notices and keep them with any redistributed models.
'''
    build_validation = json.loads((VARIANT / 'firmware/builds/validation.json').read_text())
    manifest = {'variant': VARIANT.name, 'electrical_breadboard_revision': 12,
                'firmware_source_set': build_validation['source_set'], 'enabled_emg_channels': 2,
                'imu': 'ICM-42688-P', 'included_profiles': PROFILES,
                'simulation_only_firmware_included': False, 'pcb_recording_binary_included': False,
                'synthetic_regression_fixture_included': True,
                'frozen_synthetic_recording_included': True,
                'physical_measurements_completed': 0, 'html_link_rewrites': rewritten_pages,
                'files': {name: {'sha256': checksum(data),
                                 'original_source_sha256': checksum(files[name].read_bytes()) if name in files else None}
                          for name, data in sorted(content.items())}}
    content['package-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive = VARIANT / 'breadboard/breadboard-lab-kit.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for name, data in sorted(content.items()):
            entry = zipfile.ZipInfo(ARCHIVE_ROOT + '/' + name, date_time=(2026, 10, 3, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            output.writestr(entry, data)

    # Check archive bytes, included application identities and absence of simulator images.
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for name, item in manifest['files'].items():
            assert checksum(zipped.read(ARCHIVE_ROOT + '/' + name)) == item['sha256'], name
        binaries = {name for name in content if name.endswith('.bin')}
        assert len(binaries) == len(PROFILES) * 3
        assert all(any(name.startswith('firmware/builds/' + p + '/') for p in PROFILES) for name in binaries)
        for profile in build_validation['profiles']:
            if profile['profile'] in PROFILES:
                for name, expected in profile['sha256'].items():
                    key = 'firmware/builds/' + profile['profile'] + '/' + name
                    assert checksum(content[key]) == expected, key
    receipt = {'filename': archive.name, 'bytes': archive.stat().st_size,
               'sha256': checksum(archive.read_bytes()), 'files': len(content),
               'included_profiles': PROFILES, 'binary_hash_checks': len(binaries),
               'status': 'PASS', 'physical_measurements_completed': 0,
               'note': 'Current breadboard lab kit; full project and historical ZIPs are separate.'}
    (VARIANT / 'breadboard/breadboard-lab-kit.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    print(json.dumps(package(), indent=2))
