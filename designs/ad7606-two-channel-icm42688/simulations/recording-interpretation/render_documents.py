#!/usr/bin/env python3
"""Render the focused verification guides with the existing project stylesheet."""
from pathlib import Path
import re
from markdown_it import MarkdownIt

P = Path(__file__).resolve().parent
DOCS = P.parents[1] / 'docs'
template = (DOCS / 'integrated-verification.html').read_text().split('<h1>', 1)[0]
nav = '<nav><a href="whole-system.html">Complete system</a> / <a href="data-interpretation.html">Saved data</a> / <a href="digital-timing.html">Digital timing</a> / <a href="integrated-verification.html">Integrated verification</a> / <a href="circuit-audit.html">Circuit audit</a> / <a href="lab-quickstart.html">Lab sequence</a></nav>'
template = template[:template.index('<nav>')] + nav
renderer = MarkdownIt('commonmark', {'html': True}).enable('table')
titles = {'whole-system': 'Complete system', 'integrated-verification': 'Integrated recorder verification',
          'digital-timing': 'Digital timing verification', 'data-interpretation': 'Saved data and interpretation',
          'validation-report': 'Current validation'}
for name, title in titles.items():
    prefix = re.sub(r'<title>.*?</title>', f'<title>{title} — AD7606 two-channel</title>', template)
    (DOCS / f'{name}.html').write_text(prefix + renderer.render((DOCS / f'{name}.md').read_text()) + '</main></body></html>\n')
print('Rendered five focused guides with data/timing navigation')
