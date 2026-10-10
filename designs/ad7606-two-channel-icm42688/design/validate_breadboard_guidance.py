#!/usr/bin/env python3
"""Check lab handoff pin identities, firmware hashes and blank result sheets."""
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re

VARIANT = Path(__file__).resolve().parent.parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


class LinkReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links += [value for key, value in attrs if key == 'href' and value]


def validate():
    wires = json.loads((VARIANT / 'breadboard/system-wiring.json').read_text())['connections']
    assert len(wires) == 184
    wire_by_id = {w['id']: w for w in wires}
    tables = [read_csv(VARIANT / 'breadboard' / name)
              for name in ['system-wiring.csv', 'exact-wire-endpoints.csv']]
    assert tables[0] == tables[1] and len(tables[0]) == len(wires)
    table_by_id = {r['Wire']: r for r in tables[0]}
    guide_html = (VARIANT / 'docs/build-guide.html').read_text()
    for wire in wires:
        row = table_by_id[wire['id']]
        assert row['Net'] == wire['net'] and row['Stage'] == str(wire['stage'])
        assert row['From'] == wire['a']['module'] + ':' + wire['a']['terminal']
        assert row['To'] == wire['b']['module'] + ':' + wire['b']['terminal']
        assert row['Instructions'] == wire['note']
        match = re.search(r'<tr><td>' + re.escape(wire['id']) +
                          r'</td>(?:<td>.*?</td>){4}<td>(.*?)</td></tr>', guide_html)
        assert match and html.unescape(match[1]) == wire['note'], wire['id']

    board = (VARIANT / 'firmware/main/board.h').read_text()
    pin_names = ['ADC_CONVST', 'ADC_DRDY', 'ADC_RESET', 'ADC_SCK', 'ADC_MISO', 'ADC_CS',
                 'IMU_MOSI', 'IMU_MISO', 'IMU_SCK', 'FOOT_CS', 'SHANK_CS',
                 'FOOT_INT', 'SHANK_INT', 'SD_CLK', 'SD_D0', 'USB_PRESENT_PIN']
    pins = {name: int(re.search(r'^#define ' + name + r' (\d+)$', board, re.M)[1])
            for name in pin_names}
    pins['SD_CMD'] = int(re.search(r'#if AFO_BREADBOARD\s+#define SD_CMD (\d+)', board)[1])
    pins['USB_PRESENT_N'] = pins.pop('USB_PRESENT_PIN')
    for net, gpio in pins.items():
        ends = [e for w in wires if w['net'] == net for e in [w['a'], w['b']]
                if e['module'] == 'esp']
        assert len(ends) == 1 and int(re.search(r'GPIO(\d+)', ends[0]['terminal'])[1]) == gpio, (net, gpio, ends)

    # Independently require both conversion groups on the same five-hole strip.
    trigger = [w for w in wires if w['net'] == 'ADC_CONVST']
    assert len(trigger) == 3
    assert {e['terminal'].split(' /')[0] for w in trigger for e in [w['a'], w['b']]
            if e['module'] == 'adc'} == {'CVA', 'CVB'}
    strips = [e for w in trigger for e in [w['a'], w['b']] if e['module'] == 'DIST1']
    assert {e['hole'] for e in strips} == {'a29', 'b29', 'c29'}
    assert wire_by_id['wire-111']['b']['terminal'].startswith('DB7 /')
    assert wire_by_id['wire-113']['b']['terminal'].startswith('BUSY /')

    probes = read_csv(VARIANT / 'breadboard/probe-connections.csv')
    assert len(probes) == 18
    for probe in probes:
        assert all(probe[key] == table_by_id[probe['Wire']][key]
                   for key in ['Wire', 'Stage', 'Net', 'From', 'To']), probe
        assert probe['Probe_at'] in [probe['From'], probe['To']]
    assert {'ADC_CONVST', 'ADC_DRDY', 'ADC_CS', 'ADC_SCK', 'ADC_MISO', 'ADC_RESET',
            'FOOT_INT', 'SHANK_INT', 'SD_CMD', 'SD_CLK', 'SD_D0', 'USB_PRESENT_N'} <= {p['Net'] for p in probes}

    validation = json.loads((VARIANT / 'firmware/builds/validation.json').read_text())
    assert validation['source_set'] == 'ad7606-2ch-1.7'
    for path, expected in validation['source_sha256'].items():
        assert sha256(VARIANT / 'firmware' / path) == expected, path
    assert len(validation['profiles']) == 7
    profiles = {p['profile']: p for p in validation['profiles']}
    for name, profile in profiles.items():
        assert profile['active_channels'] == 2
        for path, expected in profile['sha256'].items():
            assert sha256(VARIANT / 'firmware/builds' / name / path) == expected, (name, path)

    checks = read_csv(VARIANT / 'docs/bench-checklist.csv')
    assert len(checks) == 30 and {int(c['Stage']) for c in checks} == set(range(1, 11))
    measurement_fields = ['Firmware_application_sha256', 'Module_serial_or_photo', 'Date_operator',
                          'Instrument_calibration', 'Measured_values', 'Evidence_files', 'Reviewer']
    for check in checks:
        assert check['Outcome'] == 'NOT TESTED'
        assert all(not check[name] for name in measurement_fields), check['Check']
        if check['Firmware_profile']:
            assert profiles[check['Firmware_profile']]['hardware'] == 'breadboard', check
    guide = json.loads((VARIANT / 'viewer/guide.json').read_text())
    assert len(guide['stages']) == 10
    assert guide['stages'][4]['title'] == 'Second EMG channel'
    assert '8 kHz ±0.1%' in guide['stages'][2]['acceptance']
    assert 'GPIO47' in '\n'.join(guide['stages'][6]['tests'])

    link_count = 0
    for filename in ['breadboard-refinements.html', 'lab-quickstart.html',
                     'staged-build-guide.html', 'physical-assembly.html', 'firmware-build-guide.html',
                     'laptop-setup.html', 'download-checks.html']:
        page = VARIANT / 'docs' / filename
        links = LinkReader()
        links.feed(page.read_text())
        for link in links.links:
            if link.startswith(('http:', 'https:', '#', 'mailto:')):
                continue
            path = link.split('#', 1)[0].split('?', 1)[0]
            assert (page.parent / path).exists(), (filename, link)
            link_count += 1

    inputs = ['breadboard/system-wiring.json', 'breadboard/system-wiring.csv',
              'breadboard/exact-wire-endpoints.csv', 'breadboard/probe-connections.csv',
              'docs/bench-checklist.csv', 'docs/build-guide.html', 'viewer/guide.json',
              'firmware/main/board.h', 'firmware/builds/validation.json',
              'docs/breadboard-refinements.html', 'docs/lab-quickstart.html',
              'docs/staged-build-guide.html', 'docs/physical-assembly.html',
              'docs/firmware-build-guide.html', 'docs/laptop-setup.html', 'docs/download-checks.html',
              'host/check_package.py', 'host/run_tests.py', 'breadboard/recording-example.json',
              'breadboard/recording-example.afolog', 'design/validate_breadboard_guidance.py']
    result = {'scope': 'AD7606 fixed-two ICM breadboard handoff', 'status': 'PASS',
              'wire_table_rows': len(wires), 'firmware_pin_comparisons': len(pins),
              'probe_contacts_verified': len(probes), 'compiled_profiles_hash_verified': len(profiles),
              'unmeasured_checklist_rows': len(checks), 'rendered_local_links_verified': link_count,
              'physical_measurements_completed': 0, 'lab_binaries_executed': False,
              'source_sha256': {name: sha256(VARIANT / name) for name in inputs},
              'note': 'Static instruction/pin/hash checks; not electrical measurements or fresh firmware execution.'}
    (VARIANT / 'breadboard/guidance-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(json.dumps(validate(), indent=2))
