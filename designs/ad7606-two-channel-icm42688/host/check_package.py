#!/usr/bin/env python3
"""Check an extracted breadboard kit and decode its frozen synthetic recording."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from convert import convert

ROOT = Path(__file__).resolve().parents[1]


def verify():
    manifest = json.loads((ROOT / 'package-manifest.json').read_text())
    verified = 0
    for name, item in manifest['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Manifest path leaves the kit: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Missing or changed package file: ' + name)
        verified += 1
    source = ROOT / 'breadboard/recording-example.afolog'
    expected = json.loads((ROOT / 'breadboard/recording-example.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != expected['sha256']:
        raise ValueError('Example recording hash mismatch')
    with tempfile.TemporaryDirectory(prefix='recorder-kit-check-') as folder:
        output = Path(folder) / 'csv'
        quality = convert(source, output, make_plots=False)
        metadata = json.loads((output / 'metadata.json').read_text())['recorded']
        if quality['counts'] != expected['counts']:
            raise ValueError('Unexpected example record counts')
        if not all(quality[key] for key in ['synthetic', 'session_finalized',
                                         'structurally_complete', 'no_detected_sample_loss',
                                         'signal_checks_pass']):
            raise ValueError('Example quality checks failed')
        if quality['research_ready'] or metadata['active_channel_count'] != 2:
            raise ValueError('Example identity or validation status is incorrect')
        if metadata['adc_model'] != 'AD7606':
            raise ValueError('Unexpected ADC identity')
        with (output / 'emg.csv').open(newline='') as stream:
            reader = csv.DictReader(stream)
            if 'ch1_raw' not in reader.fieldnames or 'ch2_raw' in reader.fieldnames:
                raise ValueError('CSV does not expose exactly two EMG inputs')
            rows = 0
            for row in reader:
                for channel in (0, 1):
                    voltage = int(row[f'ch{channel}_raw']) * 5 / 32768
                    if abs(float(row[f'ch{channel}_adc_input_v']) - voltage) > 1e-9:
                        raise ValueError('EMG voltage scaling mismatch')
                    if abs(float(row[f'ch{channel}_myoware_raw_v_estimate']) - voltage) > 1e-9:
                        raise ValueError('RAW reconstruction offset mismatch')
                rows += 1
            if rows != expected['counts']['emg']:
                raise ValueError('CSV row count mismatch')
        flags = 0
        for sensor in ['foot', 'shank']:
            with (output / f'{sensor}.csv').open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != expected['counts'][sensor]:
                raise ValueError('IMU row count mismatch: ' + sensor)
            for row in rows:
                if int(row['flags']) & 2:
                    flags += 1
        if flags != expected['timing_estimate_records']:
            raise ValueError('IMU timing-estimate flags were not preserved')
    return {'status': 'PASS', 'package_files_verified': verified,
            'recording_sha256': expected['sha256'], 'converted_counts': quality['counts'],
            'imu_timing_estimate_records': flags, 'exported_emg_channels': 2,
            'synthetic': True, 'research_ready': False, 'physical_measurements_completed': 0,
            'note': 'Integrity and saved-data checks only. Run host/run_tests.py separately; '
                    'this command does not execute ESP32 hardware or test physical wiring.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Save the check receipt to a new JSON file')
    args = parser.parse_args()
    try:
        result = verify()
        text = json.dumps(result, indent=2) + '\n'
        if args.out:
            with args.out.open('x') as stream:
                stream.write(text)
        print(text, end='')
    except (OSError, ValueError, KeyError) as error:
        print('Package check failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
