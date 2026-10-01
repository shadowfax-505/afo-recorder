"""Verify the expanded drawing without relabeling it as electrical validation."""
from pathlib import Path
import hashlib
import json
import sys

P = Path(__file__).resolve().parent
S = P.parent / 'web'


def verify():
    full = json.loads((P / 'diagram.json').read_text())
    original = json.loads((S / 'diagram.json').read_text())
    manifest = json.loads((P / 'manifest.json').read_text())
    parts = {p['id']: p for p in full['parts']}
    assert len(parts) == len(full['parts']), 'duplicate part IDs'
    edges = {tuple(c[:2]) for c in full['connections']}
    for edge in original['connections']:
        assert tuple(edge[:2]) in edges, f'Lost executed connection: {edge[:2]}'
    for identity in ['esp', 'adc', 'foot', 'shank', 'fixture', 'logic']:
        assert parts[identity]['type'] == next(p['type'] for p in original['parts'] if p['id'] == identity)
    for name, extra in manifest['extra_passive_pins'].items():
        assert (P / f'{name}.chip.c').read_bytes() == (S / f'{name}.chip.c').read_bytes()
        old = json.loads((S / f'{name}.chip.json').read_text())
        new = json.loads((P / f'{name}.chip.json').read_text())
        assert new == dict(old, pins=old['pins'] + extra), 'Unexpected model definition change'
    # Context interfaces agree with the laboratory GPIO profile. No SPI card is
    # substituted onto different pins and no GPIO is invented for internal Wi-Fi.
    gpio = json.loads((P.parents[2] / 'design/breadboard-gpio-map.json').read_text())
    expected = {'sd:CLK': ('39', 'SD_CLK_MCU'), 'sd:CMD': ('47', 'SD_CMD'),
                'sd:D0': ('40', 'SD_D0'), 'usb:D_MINUS': ('19', 'USB_DM_MCU'),
                'usb:D_PLUS': ('20', 'USB_DP_MCU'), 'monitor:USB_N': ('21', 'USB_PRESENT_N'),
                'monitor:BAT_ADC': ('1', 'BAT_SENSE'), 'button:1.l': ('18', 'BUTTON')}
    for pin, (number, net) in expected.items():
        assert gpio[number] == net
        assert (pin, f'esp:{number}') in edges or (f'esp:{number}', pin) in edges
    for name, digest in manifest['sha256'].items():
        assert hashlib.sha256((P/name).read_bytes()).hexdigest() == digest
    for name in manifest['passive_context_types']:
        source = (P / f'{name}.chip.c').read_text()
        assert 'void chip_init(void) {}' in source
        assert not any(word in source for word in ['pin_write(', 'timer_start(', 'pin_watch('])
    return {'pass': True, 'parts': len(parts), 'connections': len(edges),
            'original_executable_connections_preserved': len(original['connections']),
            'protocol_c_sources_byte_identical': True, 'lab_context_gpio_matches': True,
            'passive_blocks_have_no_callbacks_or_pin_drives': True,
            'electrical_or_physical_validation': False}


if __name__ == '__main__':
    result = verify()
    (P / 'scene-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
