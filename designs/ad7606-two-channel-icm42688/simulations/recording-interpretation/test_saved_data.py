#!/usr/bin/env python3
"""Challenge the saved-data audit with damaged bytes and misleading exports."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from verify_saved_data import P, audit_case, read_binary

SOURCE = P.parent / 'integrated-recorder/full-system/trace-validation/probe-run'


def change_csv(folder, name, change):
    path = folder / f'converted/{name}.csv'
    with path.open(newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    change(fields, rows)
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fields); writer.writeheader(); writer.writerows(rows)


def main():
    before = {f.relative_to(SOURCE).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in SOURCE.rglob('*') if f.is_file()}
    tests = []
    raw = (SOURCE / 'recorder-output.raw').read_bytes()
    for name, contents in [('truncated-header', raw[:4095]), ('truncated-record', raw[:-1]),
                           ('header-crc-corruption', raw[:100] + bytes([raw[100] ^ 1]) + raw[101:]),
                           ('record-crc-corruption', raw[:4200] + bytes([raw[4200] ^ 1]) + raw[4201:])]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'damaged.raw'; path.write_bytes(contents)
            try: read_binary(path)
            except ValueError as error: tests.append(dict(name=name, rejected=True, reason=str(error)))
            else: raise AssertionError(f'Accepted {name}')
    alterations = [
        ('wrong-voltage-units', 'emg', lambda f, r: r[0].update(ch0_adc_input_v='1000.06103515625')),
        ('swapped-emg-channels', 'emg', lambda f, r: r[0].update(ch0_raw=r[0]['ch1_raw'])),
        ('hidden-disabled-channel', 'emg', lambda f, r: f.append('ch2_raw')),
        ('csv-row-missing', 'emg', lambda f, r: r.pop(10)),
        ('wrong-imu-axis-scaling', 'foot', lambda f, r: r[0].update(az_g='16.0')),
        ('unflagged-imu-time', 'shank', lambda f, r: r[0].update(flags='0')),
        ('wrong-final-counter', 'status', lambda f, r: r[-1].update(emg_records='10040')),
    ]
    for name, stream, change in alterations:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'run'; folder.mkdir()
            for file in ['recorder-output.raw', 'simulated-recording.afolog', 'live-results.json']:
                shutil.copy2(SOURCE / file, folder / file)
            shutil.copytree(SOURCE / 'converted', folder / 'converted')
            shutil.copytree(SOURCE / 'live-capture', folder / 'live-capture')
            change_csv(folder, stream, change)
            try: audit_case(folder)
            except ValueError as error: tests.append(dict(name=name, rejected=True, reason=str(error)))
            else: raise AssertionError(f'Accepted {name}')
    after = {f.relative_to(SOURCE).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
             for f in SOURCE.rglob('*') if f.is_file()}
    assert before == after, 'Tests altered source evidence'
    result = dict(passed=True, damaged_cases_rejected=len(tests), tests=tests,
                  source_evidence_unchanged=True, hardware_measured=False)
    (P / 'audit-tests.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'damaged_cases_rejected': len(tests)}))


if __name__ == '__main__': main()
