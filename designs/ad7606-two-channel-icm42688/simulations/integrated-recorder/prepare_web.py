#!/usr/bin/env python3
"""Prepare the same behavioral models for Wokwi's web custom-chip compiler."""
from pathlib import Path
import hashlib
import json

P = Path(__file__).resolve().parent


def prepare():
    destination = P / 'web'
    destination.mkdir(exist_ok=True)
    names = ['diagram.json']
    (destination / 'diagram.json').write_bytes((P / 'diagram.json').read_bytes())
    sources = {}
    for model in ('ad7606', 'icm42688', 'fixture'):
        for suffix in ('c', 'json'):
            name = f'{model}.chip.{suffix}'
            source = P / 'chips' / name
            data = source.read_text()
            sources[f'chips/{name}'] = hashlib.sha256(source.read_bytes()).hexdigest()
            if name == 'ad7606.chip.c':
                header = P / 'chips/stimulus.h'
                sources['chips/stimulus.h'] = hashlib.sha256(header.read_bytes()).hexdigest()
                assert data.count('#include "stimulus.h"') == 1
                # Web builds cannot resolve an additional arbitrary header tab.
                # A pragma intended for a header is invalid in the merged C file
                # under the web compiler's -Werror. Leave its line as a blank.
                stimulus = header.read_text().replace('#pragma once', '')
                data = data.replace('#include "stimulus.h"', stimulus)
            (destination / name).write_text(data)
            names.append(name)
    manifest = dict(simulation_only=True, hardware_measured=False,
                    transformations=['Inline stimulus.h in ad7606.chip.c',
                                     'Remove header-only pragma once; preserve its blank line'],
                    changed_model_callbacks=False,
                    source_sha256=sources,
                    web_sha256={name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                                for name in names})
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': len(names), 'changed_model_callbacks': False}))


if __name__ == '__main__':
    prepare()
