#!/usr/bin/env python3
"""Render the sequential workbook and personal briefing from editable sources."""
from pathlib import Path
import re,html,json,math
from markdown_it import MarkdownIt
P=Path(__file__).resolve().parents[1]
md=MarkdownIt('commonmark',{'html':False}).enable('table')
css='''body{margin:0;background:#edf0ed;color:#172c29;font:17px/1.65 system-ui,sans-serif}main{max-width:940px;margin:32px auto;padding:42px;background:#fff;border-top:6px solid #0b7766;border-radius:6px}nav{display:flex;gap:20px;flex-wrap:wrap;font-size:14px;border-bottom:1px solid #d5dfdb;padding-bottom:18px}a{color:#096b60;text-underline-offset:3px}h1{font-size:38px;line-height:1.15;letter-spacing:-1px}h2{font-size:25px;margin-top:38px}h3{font-size:20px}table{border-collapse:collapse;width:100%;font-size:14px;display:block;overflow-x:auto}th,td{padding:10px;text-align:left;border:1px solid #dce5df;vertical-align:top}th{background:#e8f2ee}li{margin:8px 0}code{background:#f0f3f0;padding:2px 5px}footer{font-size:13px;margin-top:40px;border-top:1px solid #ddd;padding-top:15px}@media(max-width:650px){main{margin:0;padding:22px}h1{font-size:30px}}'''
files=list((P/'development').glob('**/*.md'))+[P/'docs/understanding-the-recorder.md']
for source in files:
 output=source.with_suffix('.html')
 if source==P/'development/README.md':output=P/'development/index.html'
 text=source.read_text()
 text=re.sub(r'\]\(([^)]+)\.md\)',lambda m:']('+m.group(1)+('.html' if not m.group(1).endswith('../README') else '.html')+')',text)
 text=text.replace('](../README.html)','](../index.html)')
 if source.parent==P/'development':home='../'
 elif source.parent.parent==P/'development':home='../../'
 else:home='../'
 title=source.read_text().splitlines()[0].lstrip('# ')
 body=md.render(text)
 output.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+css+'</style></head><body><main><nav><a href="'+home+'development/index.html">Build sequence</a><a href="'+home+'docs/understanding-the-recorder.html">How it works</a><a href="'+home+'viewer/build.html">Assembly workspace</a><a href="'+home+'docs/understanding-the-recorder.pdf">Briefing PDF</a></nav>'+body+'<footer>Muttakin Rahman · AD7606 / two-channel / ICM-42688-P · Physical validation pending</footer></main></body></html>')
# Keep the detailed handbook and circuit pack reproducible.
from build_supervisor_documents import build
build()
