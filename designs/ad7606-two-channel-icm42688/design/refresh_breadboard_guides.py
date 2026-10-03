#!/usr/bin/env python3
"""Refresh this variant's wire tables and rendered lab instructions."""
import csv
import html
import json
from pathlib import Path
import re

from markdown_it import MarkdownIt

VARIANT = Path(__file__).resolve().parent.parent


def refresh_wire_tables():
    wires = json.loads((VARIANT / 'breadboard/system-wiring.json').read_text())['connections']
    fields = ['Wire', 'Stage', 'Net', 'From', 'To', 'Instructions']
    rows = [dict(zip(fields, [w['id'], w['stage'], w['net'],
                             w['a']['module'] + ':' + w['a']['terminal'],
                             w['b']['module'] + ':' + w['b']['terminal'], w['note']]))
            for w in wires]
    for name in ['system-wiring.csv', 'exact-wire-endpoints.csv']:
        with (VARIANT / 'breadboard' / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\r\n')
            writer.writeheader()
            writer.writerows(rows)

    path = VARIANT / 'docs/build-guide.html'
    text = path.read_text()
    for row in rows:
        pattern = (r'(<tr><td>' + re.escape(row['Wire']) +
                   r'</td>(?:<td>.*?</td>){4}<td>)(.*?)(</td></tr>)')
        text, count = re.subn(pattern, lambda m: m[1] + html.escape(row['Instructions']) + m[3], text)
        if count != 1:
            raise ValueError(f"Expected exactly one assembly-table row for {row['Wire']}; found {count}")

    old_status = r'<p><strong>Current v1\.6 / preserved v1\.5 evidence:</strong>.*?</p>'
    replacement = ('<p><strong>Current breadboard handoff:</strong> '
                   '<a href="breadboard-refinements.html">Applied simulation findings</a> · '
                   '<a href="lab-quickstart.html">Short lab sequence</a> · '
                   '<a href="bench-checklist.csv">Blank bench checklist</a> · '
                   '<a href="../breadboard/probe-connections.csv">Exact probe contacts</a> · '
                   '<a href="../breadboard/breadboard-lab-kit.zip">Current lab kit</a>. '
                   'Use v1.6 laboratory profiles. See '
                   '<a href="integrated-verification.html">current integrated results</a>, '
                   '<a href="digital-timing.html">digital timing</a> and '
                   '<a href="data-interpretation.html">saved-data interpretation</a> for evidence and limits. '
                   'Every physical measurement remains unperformed; simulation results do not fill lab result cells.</p>')
    text, count = re.subn(old_status, replacement, text)
    if count == 0 and '<strong>Current breadboard handoff:</strong>' not in text:
        raise ValueError('Assembly-table evidence banner not found')
    path.write_text(text)
    return len(rows)


def render_lab_guides():
    docs = VARIANT / 'docs'
    template = (docs / 'lab-quickstart.html').read_text().split('<h1>', 1)[0]
    nav = ('<nav><a href="../viewer/build.html">Assembly workspace</a> / '
           '<a href="breadboard-refinements.html">Applied findings</a> / '
           '<a href="lab-quickstart.html">Lab sequence</a> / '
           '<a href="build-guide.html">Wire tables</a> / '
           '<a href="laptop-setup.html">Laptop setup</a> / '
           '<a href="data-interpretation.html">Saved data</a> / '
           '<a href="integrated-verification.html">Verification</a></nav>')
    template = template[:template.index('<nav>')] + nav
    renderer = MarkdownIt('commonmark', {'html': True}).enable('table')
    titles = {'lab-quickstart': 'Build one working stage at a time',
              'breadboard-refinements': 'Breadboard updates from simulation',
              'staged-build-guide': 'Staged breadboard build',
              'physical-assembly': 'Physical assembly',
              'firmware-build-guide': 'Firmware profiles and rebuilding',
              'laptop-setup': 'Start the downloaded lab kit',
              'download-checks': 'Checks on the downloaded breadboard kit'}
    for name, title in titles.items():
        prefix = re.sub(r'<title>.*?</title>', f'<title>{title} — AD7606 two-channel</title>', template)
        (docs / f'{name}.html').write_text(prefix + renderer.render((docs / f'{name}.md').read_text()) +
                                         '</main></body></html>\n')


if __name__ == '__main__':
    print(f'Refreshed {refresh_wire_tables()} wire instructions and focused lab guides')
    render_lab_guides()
