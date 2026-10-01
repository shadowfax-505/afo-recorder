#!/usr/bin/env python3
"""Validate saved web-editor transcripts with the production converters.

Browser execution is manual. This tool does not invent an execution result,
replace absent transcripts, or infer current-image success from older evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import run as integrated

P = Path(__file__).resolve().parent
ROOT = P.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assess_case(case, out):
    manifest = json.loads((out / 'tested-build.json').read_text())
    for name, digest in manifest['sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError(f'tested build differs from release: {name}')
    actual = json.loads((out / 'diagram.json').read_text())
    expected = integrated.make_diagram(case)
    # Explicit zero attributes and omitted attributes have identical defaults.
    for diagram in (actual, expected):
        for part in diagram['parts']:
            for key in ('fault', 'waveform'):
                if part.get('attrs', {}).get(key) == '0':
                    del part['attrs'][key]
    if actual != expected:
        raise ValueError('saved diagram differs from the specified fault injection')
    text = (out / 'serial.txt').read_text()
    elf_prefix = manifest['sha256'][
        'simulations/integrated-recorder/firmware/integrated_recorder.elf'][:9]
    if f'ELF file SHA256:  {elf_prefix}' not in text:
        raise ValueError('serial boot identification does not match the current ELF')
    # The converter deliberately refuses nonempty directories. Reverify in a
    # fresh directory, preserving prior evidence rather than erasing it.
    with tempfile.TemporaryDirectory(prefix='afo-web-check-') as temporary:
        checked = Path(temporary)
        result = integrated.assess(case, text, checked)
        for name in ('recorder-output.raw', 'udp-output.raw'):
            old, new = out / name, checked / name
            if old.exists() and new.exists() and old.read_bytes() != new.read_bytes():
                raise ValueError(f'existing original evidence differs: {name}')
        for source in checked.iterdir():
            destination = out / source.name
            if destination.exists():
                continue
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copyfile(source, destination)
    result.update(case=case, engine='Wokwi web editor',
                  firmware='ad7606-2ch-1.6', hardware_measured=False,
                  serial_sha256=sha(out / 'serial.txt'),
                  assessor_sha256=sha(P / 'run.py'),
                  merged_image_sha256=manifest['sha256'][
                      'simulations/integrated-recorder/firmware/merged.bin'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=P / 'results/web-current')
    parser.add_argument('--case', choices=list(integrated.CASES))
    args = parser.parse_args()
    cases = [args.case] if args.case else list(integrated.CASES)
    rows = []
    for case in cases:
        out = args.results / case
        if not (out / 'serial.txt').is_file():
            rows.append({'case': case, 'pass': None, 'executed': False})
            continue
        try:
            result = assess_case(case, out)
        except (ValueError, OSError, KeyError) as exc:
            result = {'case': case, 'pass': False, 'error': str(exc),
                      'engine': 'Wokwi web editor', 'hardware_measured': False}
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        rows.append(dict(result, executed=True))
        print(json.dumps({k: result[k] for k in ('case', 'pass', 'error') if k in result}))
    if not args.case:
        summary = dict(engine='Wokwi web editor', firmware='ad7606-2ch-1.6',
                       hardware_measured=False, planned_cases=len(cases),
                       executed_cases=sum(x['executed'] for x in rows),
                       passed_cases=sum(x['pass'] is True for x in rows),
                       full_matrix_pass=all(x['pass'] is True for x in rows),
                       cases=rows)
        (args.results / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 1 if any(x['pass'] is False for x in rows) else 0


if __name__ == '__main__':
    raise SystemExit(main())
