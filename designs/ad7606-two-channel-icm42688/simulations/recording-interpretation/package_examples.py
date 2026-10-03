#!/usr/bin/env python3
"""Package actual captured synthetic recordings and verify the extracted bytes."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urljoin

from verify_saved_data import P, audit_case, equal, read_csv, require


def check_analysis(folder):
    """Compare every convenience-table row with its unchanged converter export."""
    _, emg = read_csv(folder / 'converted/emg.csv')
    _, muscle = read_csv(folder / 'analysis/muscle.csv')
    require(len(emg) == len(muscle), 'Named muscle table dropped rows')
    origin = int(emg[0]['conversion_trigger_host_us'])
    for source, row in zip(emg, muscle):
        for key, value in dict(sequence=source['sequence'],
                               time_since_first_emg_s=(int(source['conversion_trigger_host_us']) - origin) / 1e6,
                               EMG1_adc_input_V=source['ch0_adc_input_v'], EMG2_adc_input_V=source['ch1_adc_input_v'],
                               flags=source['flags']).items(): equal(row, key, value)
    for body in ['foot', 'shank']:
        _, source_rows = read_csv(folder / f'converted/{body}.csv')
        _, named_rows = read_csv(folder / f'analysis/{body}-motion.csv')
        require(len(source_rows) == len(named_rows), 'Named motion table dropped rows')
        for source, row in zip(source_rows, named_rows):
            expected = dict(sequence=source['sequence'],
                estimated_time_since_first_emg_s=(int(source['host_time_estimate_us']) - origin) / 1e6,
                sensor_time_unwrapped_us=source['sensor_time_unwrapped_us'], flags=source['flags'], valid=source['valid'])
            expected.update({a + '_g': source[a + '_g'] for a in ['ax', 'ay', 'az']})
            expected.update({a + '_deg_per_s': source[a + '_dps'] for a in ['gx', 'gy', 'gz']})
            for key, value in expected.items(): equal(row, key, value)
    interpretation = json.loads((folder / 'analysis/interpretation.json').read_text())
    require(interpretation['time_origin_host_us'] == origin and interpretation['synthetic'] is True
            and interpretation['research_ready'] is False, 'Named table provenance')


def package():
    integrated = P.parent / 'integrated-recorder'
    sources = {'known-dc': integrated / 'full-system/trace-validation/probe-run',
               'synthetic-waveform': integrated / 'results/web-current/filtered-synthetic-emg'}
    stimulus = integrated / 'stimulus/filtered-samples.csv'
    files = {name: (P / name).read_bytes() for name in
             ['README.md', 'verify_saved_data.py', 'analyze_example.py', 'results.json', 'audit-tests.json',
              'saved-signals.png', 'saved-signals.svg']}
    files['examples/filtered-samples.csv'] = stimulus.read_bytes()
    files['examples/stimulus-summary.json'] = (integrated / 'stimulus/summary.json').read_bytes()
    guide = (P.parents[1] / 'docs/data-interpretation.html').read_text()
    local = {'../simulations/recording-interpretation/saved-signals.png': 'saved-signals.png',
             '../simulations/recording-interpretation/results.json': 'results.json',
             '../simulations/recording-interpretation/audit-tests.json': 'audit-tests.json'}
    base = 'https://shadowfax-505.github.io/afo-recorder/designs/ad7606-two-channel-icm42688/docs/'
    guide = re.sub(r'(href|src)="([^"]+)"',
                   lambda m: f'{m[1]}="{local.get(m[2], urljoin(base, m[2]))}"', guide)
    files['data-guide.html'] = guide.encode()
    with tempfile.TemporaryDirectory() as temp:
        for name, source in sources.items():
            result = audit_case(source, stimulus if name == 'synthetic-waveform' else None)
            assert result['passed']
            selected = ['recorder-output.raw', 'simulated-recording.afolog', 'live-results.json',
                        'result.json', 'tested-build.json', 'diagram.json']
            for path in sorted((source / 'converted').glob('*')):
                if path.is_file(): selected.append(path.relative_to(source).as_posix())
            for path in sorted((source / 'live-capture').glob('*.afolog')):
                selected.append(path.relative_to(source).as_posix())
            for relative in selected: files[f'examples/{name}/{relative}'] = (source / relative).read_bytes()
            output = Path(temp) / name
            subprocess.run([sys.executable, str(P / 'analyze_example.py'), str(source / 'converted'), str(output)],
                           check=True, capture_output=True, text=True)
            for path in sorted(output.glob('*')): files[f'examples/{name}/analysis/{path.name}'] = path.read_bytes()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    contents = dict(synthetic=True, hardware_measured=False, research_ready=False,
                    recorder_firmware='ad7606-2ch-1.6', sha256_contents=hashes)
    files['bundle-manifest.json'] = (json.dumps(contents, indent=2) + '\n').encode()
    output = P / 'recording-examples.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    with tempfile.TemporaryDirectory() as temp, zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, data in files.items(): assert archive.read(name) == data, name
        archive.extractall(temp)
        for name in sources: check_analysis(Path(temp) / 'examples' / name)
        result = subprocess.run([sys.executable, str(Path(temp) / 'verify_saved_data.py'),
                                 '--examples', str(Path(temp) / 'examples'),
                                 '--output', str(Path(temp) / 'checked-results.json')],
                                check=True, capture_output=True, text=True)
        assert json.loads((Path(temp) / 'checked-results.json').read_text()) == json.loads((P / 'results.json').read_text())
    report = dict(file=output.name, bytes=output.stat().st_size,
                  sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  synthetic=True, hardware_measured=False, research_ready=False,
                  standalone_extracted_audit_passed=True, named_analysis_table_parity_passed=True,
                  offline_guide_included=True, sha256_contents=hashes)
    (P / 'download.json').write_text(json.dumps(report, indent=2) + '\n')
    (P / 'recording-examples.zip.sha256').write_text(f"{report['sha256']}  {output.name}\n")
    print(json.dumps({k: report[k] for k in ['file', 'bytes', 'sha256', 'standalone_extracted_audit_passed']}))


if __name__ == '__main__': package()
