"""Add an input-only timing instrument to the unchanged complete-system scene."""
from pathlib import Path
import hashlib
import json
import re

P = Path(__file__).resolve().parent
CONNECTIONS = {
    'CONVST': 'adc:CONVST', 'BUSY': 'adc:BUSY', 'CS': 'adc:CS',
    'SCLK': 'adc:SCLK', 'DOUTA': 'adc:DOUTA', 'FOOT_IRQ': 'foot:INT1',
    'SHANK_IRQ': 'shank:INT1', 'FOOT_CS': 'foot:CS', 'RESET': 'adc:RESET',
    'GND': 'esp:GND.1',
}


def prepare():
    scene = json.loads((P.parent / 'diagram.json').read_text())
    scene['parts'].extend([
        {'type': 'chip-probe', 'id': 'probe', 'left': 730, 'top': 525, 'attrs': {}},
        {'type': 'wokwi-text', 'id': 'probe_note', 'left': 720, 'top': 645,
         'attrs': {'text': 'INPUT-ONLY VIRTUAL PROBE\nTiming + decoded words: Chips Console\nFirst two frames: recorded edge trace\nNo electrical or manufacturer validation.', 'fontSize': '12'}},
    ])
    scene['connections'].extend([[net, f'probe:{pin}', '', []] for pin, net in CONNECTIONS.items()])
    (P / 'diagram.json').write_text(json.dumps(scene, indent=2) + '\n')
    source = (P / 'probe.chip.c').read_text()
    assert not re.search(r'\b(?:pin_write|pin_mode|pin_watch_stop)\s*\(', source), 'Probe drives or removes a watch'
    assert re.search(r'pin_init\(names\[i\], INPUT\)', source)
    assert not re.search(r'\b(?:INPUT_PULLUP|INPUT_PULLDOWN|OUTPUT_LOW|OUTPUT_HIGH)\b', source)
    for name in ['ad7606', 'icm42688', 'fixture']:
        assert (P.parent / f'{name}.chip.c').read_bytes() == (P.parent.parent / 'web' / f'{name}.chip.c').read_bytes()
    manifest = {
        'hardware_measured': False, 'instrument': 'Project-authored passive digital pin observer',
        'original_scene_unchanged': True, 'original_connections': len(scene['connections']) - len(CONNECTIONS),
        'added_input_taps': CONNECTIONS, 'parts': len(scene['parts']), 'connections': len(scene['connections']),
        'sensor_model_c_sources_unchanged': True,
        'sha256': {n: hashlib.sha256((P / n).read_bytes()).hexdigest()
                   for n in ['diagram.json', 'probe.chip.c', 'probe.chip.json']},
    }
    (P / 'probe-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(prepare(), indent=2))
