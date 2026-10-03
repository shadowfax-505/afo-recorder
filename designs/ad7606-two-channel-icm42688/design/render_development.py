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
# PDF uses the same source, with deliberate chapter grouping and vector flow diagram.
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCustom',fontName='Helvetica-Bold',fontSize=29,leading=34,textColor=colors.HexColor('#123d35'),spaceAfter=22))
styles.add(ParagraphStyle(name='Chapter',fontName='Helvetica-Bold',fontSize=20,leading=25,textColor=colors.HexColor('#096b60'),spaceAfter=15))
styles.add(ParagraphStyle(name='TextCustom',fontName='Helvetica',fontSize=11,leading=16,spaceAfter=12))
styles.add(ParagraphStyle(name='SmallCustom',fontName='Helvetica',fontSize=8,leading=12,spaceAfter=8))
source=(P/'docs/understanding-the-recorder.md').read_text()
sections=re.split(r'^## ',source,flags=re.M)
story=[Paragraph('Understanding my<br/>muscle and motion recorder',styles['TitleCustom']),Paragraph('Muttakin Rahman',styles['Chapter']),Paragraph('A personal briefing for AFO and neuromuscular research',styles['TextCustom']),Spacer(1,18)]
d=Drawing(490,165)
labels=['MyoWare RAW','Analog filters','AD7606','ESP32','SD / laptop']
for i,label in enumerate(labels):
 x=i*98;y=100
 d.add(Rect(x,y,88,48,rx=6,ry=6,fillColor=colors.HexColor('#e6f1ed'),strokeColor=colors.HexColor('#0b7766')))
 d.add(String(x+44,y+20,label,textAnchor='middle',fontName='Helvetica',fontSize=9))
 if i<4:
  d.add(Line(x+88,y+24,x+97,y+24,strokeColor=colors.HexColor('#0b7766')))
  d.add(Polygon([x+97,y+24,x+93,y+27,x+93,y+21],fillColor=colors.HexColor('#0b7766'),strokeColor=None))
d.add(Rect(275,15,126,42,rx=6,ry=6,fillColor=colors.HexColor('#e6f1ed'),strokeColor=colors.HexColor('#0b7766')))
d.add(String(338,32,'Foot + shank IMUs',textAnchor='middle',fontName='Helvetica',fontSize=10))
d.add(Line(338,57,338,99,strokeColor=colors.HexColor('#0b7766')))
d.add(Polygon([338,99,334,93,342,93],fillColor=colors.HexColor('#0b7766'),strokeColor=None))
story.extend([d,Paragraph('Design and simulation evidence exist. An assembled recorder has not yet been measured.',styles['TextCustom']),Paragraph('4 October 2026 · Fixed two-channel AD7606 / ICM-42688-P build',styles['SmallCustom']),PageBreak()])
for idx,section in enumerate(sections[1:]):
 title,body=section.split('\n',1)
 if idx and idx%2==0:story.append(PageBreak())
 story.append(Paragraph(html.escape(title),styles['Chapter']))
 for para in body.strip().split('\n\n'):
  para=para.replace('“','"').replace('”','"').replace('’',"'").replace('–','-').replace('—','-')
  story.append(Paragraph(html.escape(para).replace('\n','<br/>'),styles['SmallCustom' if title=='Reading and evidence' else 'TextCustom']))
def footer(canvas,doc):
 canvas.setStrokeColor(colors.HexColor('#cbd8d1'));canvas.line(48,40,547,40)
 canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#45645c'));canvas.drawString(48,27,'Muttakin Rahman | Research recorder | Physical validation pending');canvas.drawRightString(547,27,str(doc.page))
SimpleDocTemplate(str(P/'docs/understanding-the-recorder.pdf'),pagesize=(595,842),rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=55,title='Understanding my muscle and motion recorder',author='Muttakin Rahman').build(story,onFirstPage=footer,onLaterPages=footer)
