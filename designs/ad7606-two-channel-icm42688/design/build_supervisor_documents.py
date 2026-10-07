#!/usr/bin/env python3
"""Build the supervisor handbook and circuit pack from editable project sources."""
from pathlib import Path
import html, re, math, subprocess, tempfile, hashlib
from markdown_it import MarkdownIt
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderSVG
from pypdf import PdfReader, PdfWriter
P=Path(__file__).resolve().parents[1]
D=P/'docs'
TEAL=colors.HexColor('#096b60'); INK=colors.HexColor('#172c29'); LIGHT=colors.HexColor('#e8f2ee')
md=MarkdownIt('commonmark', {'html':False}).enable('table')
s=getSampleStyleSheet()
for name,size,leading in [('BodyX',10.5,15),('SmallX',8.5,12),('H1X',23,28),('H2X',13,18),('CoverX',34,39)]:
 s.add(ParagraphStyle(name=name,fontName='Helvetica-Bold' if name in ('H1X','H2X','CoverX') else 'Helvetica',fontSize=size,leading=leading,textColor=TEAL if name in ('H1X','H2X','CoverX') else INK,spaceAfter=10,keepWithNext=name in ('H1X','H2X'),splitLongWords=True))
def clean(t):
 return t.replace('–','-').replace('—','-').replace('−','-').replace('’',"'").replace('“','"').replace('”','"').replace('µ','u').replace('×','x').replace('±','+/-').replace('Ω','ohm').replace('→',' -> ')
def inline(t):
 t=html.escape(clean(t))
 t=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',t)
 t=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',t)
 t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2" color="#096b60">\1</a>',t)
 return t

def para(t,style='BodyX'):return Paragraph(inline(t),s[style])
def footer(c,d):
 c.setStrokeColor(colors.HexColor('#cbd8d1'));c.line(48,40,547,40)
 c.setFont('Helvetica',8);c.setFillColor(TEAL);c.drawString(48,27,'Muttakin Rahman | AD7606 / 2 EMG / ICM-42688-P');c.drawRightString(547,27,str(d.page))
class Document(BaseDocTemplate):
 def __init__(self,path,title):
  super().__init__(str(path),pagesize=(595,842),leftMargin=48,rightMargin=48,topMargin=48,bottomMargin=58,title=title,author='Muttakin Rahman')
  self.addPageTemplates(PageTemplate(id='normal',frames=[Frame(48,58,499,736,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=footer))
 def afterFlowable(self,f):
  if isinstance(f,Paragraph) and f.style.name=='H1X' and re.match(r'^\d+\.',f.getPlainText()):
   text=f.getPlainText();key='section-'+hashlib.sha1(text.encode()).hexdigest()[:12]
   self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,0)
   self.notify('TOCEntry',(0,text,self.page,key))
def box(d,x,y,w,h,label):
 d.add(Rect(x,y,w,h,rx=4,ry=4,fillColor=LIGHT,strokeColor=TEAL))
 for i,line in enumerate(label.split('|')):d.add(String(x+w/2,y+h/2+6-(i*13),line,textAnchor='middle',fontName='Helvetica',fontSize=9,fillColor=INK))
def arrow(d,x,y,a,b):
 d.add(Line(x,y,a,b,strokeColor=TEAL,strokeWidth=1.4))
 angle=math.atan2(b-y,a-x);u=6
 d.add(Polygon([a,b,a-u*math.cos(angle-.5),b-u*math.sin(angle-.5),a-u*math.cos(angle+.5),b-u*math.sin(angle+.5)],fillColor=TEAL,strokeColor=None))
def figure(kind):
 d=Drawing(499,220)
 if kind=='architecture':
  for x,label in [(0,'2 x MyoWare|RAW outputs'),(128,'Buffers +|two RC poles'),(256,'AD7606|8 kHz trigger'),(384,'ESP32-S3|timestamps')]:box(d,x,140,110,55,label)
  for x in (110,238,366):arrow(d,x,167,x+18,167)
  box(d,245,35,120,55,'Foot + shank|ICM-42688-P');arrow(d,365,63,439,140)
  box(d,384,35,110,55,'microSD primary|Wi-Fi preview');arrow(d,439,140,439,90)
  d.add(String(0,10,'Functional paths only; not physical header positions.',fontSize=9,fillColor=TEAL))
 elif kind=='filter':
  x0,y0,w,h=45,40,430,160
  for db in (0,-10,-20,-30):
   y=y0+h*(db+30)/30;d.add(Line(x0,y,x0+w,y,strokeColor=colors.lightgrey));d.add(String(5,y-3,str(db)+' dB',fontSize=9))
  prev=None
  for i in range(151):
   f=10**(1+i*math.log10(400)/150);db=-20*math.log10(1+(2*math.pi*f*3300*47e-9)**2)
   q=(x0+w*i/150,y0+h*(db+30)/30)
   if prev:d.add(Line(*prev,*q,strokeColor=TEAL,strokeWidth=2))
   prev=q
  for f in (10,100,500,1000,4000):d.add(String(x0+w*math.log10(f/10)/math.log10(400)-10,22,str(f),fontSize=9))
  d.add(String(190,5,'Frequency (Hz), logarithmic scale',fontSize=9))
 elif kind=='timing':
  for y,label in [(165,'CONVST'),(115,'BUSY'),(65,'Serial read')]:
   d.add(String(0,y+4,label,fontSize=9));d.add(Line(85,y,480,y,strokeColor=colors.grey))
  for x in (100,280,460):
   d.add(Line(x,165,x,190,strokeColor=TEAL));d.add(Line(x,190,x+8,190,strokeColor=TEAL));d.add(Line(x+8,190,x+8,165,strokeColor=TEAL))
  for x in (100,280):
   box(d,x+8,115,45,22,'');box(d,x+65,65,95,22,'128 clocks')
  d.add(String(175,202,'125 us between triggers (8 kHz)',fontSize=10,fillColor=TEAL))
  d.add(String(0,15,'Illustration only: widths are not measured or to scale.',fontSize=9))
 elif kind=='power':
  box(d,0,150,125,48,'Protected battery|external charging');box(d,185,150,140,48,'Regulation and|power distribution');arrow(d,125,174,185,174)
  for x,label in [(0,'5 V ADC|module / AVCC'),(173,'3.3 V digital|ESP32, IMUs, SD'),(346,'3.0 V analog|sensors / buffers')]:
   box(d,x,40,150,55,label);arrow(d,255,150,x+75,95)
  d.add(String(0,12,'Common ground. USB attachment inhibits recording.',fontSize=9,fillColor=TEAL))
 return d

def analog_channel(ch):
 d=Drawing(499,190);base=100+10*ch;y=95
 def line(x,y,a,b):d.add(Line(x,y,a,b,strokeColor=INK,strokeWidth=1))
 def label(x,y,text):d.add(String(x,y,text,fontName='Helvetica',fontSize=7.5,fillColor=INK))
 def resistor(x,y,name,value):
  line(x,y,x+8,y);d.add(Rect(x+8,y-4,28,8,fillColor=None,strokeColor=INK));line(x+36,y,x+44,y);label(x+3,y+13,name+' '+value)
 def ground(x,y):
  line(x,y,x,y-8)
  for w,dy in ((12,8),(8,11),(3,14)):line(x-w/2,y-dy,x+w/2,y-dy)
 def cap(x,y,name,value):
  line(x,y,x,y-25);line(x-6,y-25,x+6,y-25);line(x-6,y-30,x+6,y-30);line(x,y-30,x,y-42);ground(x,y-42);label(x+8,y-36,name);label(x+8,y-47,value)
 def buffer(x,y,name,pins):
  d.add(Polygon([x,y-15,x,y+15,x+32,y],fillColor=LIGHT,strokeColor=INK));label(x+3,y+3,'+');label(x+3,y-11,'-');label(x-2,y+25,name);label(x-2,y+37,pins)
  line(x+32,y,x+40,y);line(x+40,y,x+40,y-22);line(x+40,y-22,x-6,y-22);line(x-6,y-22,x-6,y-8);line(x-6,y-8,x,y-8)
 label(0,176,'EMG'+str(ch+1)+' / J'+str(ch+5)+' pin 3 / RAW'+str(ch))
 line(0,y,35,y);resistor(35,y,'R'+str(base),'3.3k');line(79,y,110,y);cap(92,y,'C'+str(base),'47nF');buffer(110,y,'U3 '+('A' if ch==0 else 'B'),'+/-/out '+('3/2/1' if ch==0 else '5/6/7'))
 line(150,y,177,y);resistor(177,y,'R'+str(base+2),'3.3k');line(221,y,265,y);cap(244,y,'C'+str(base+1),'47nF');buffer(265,y,'U4 '+('A' if ch==0 else 'B'),'+/-/out '+('3/2/1' if ch==0 else '5/6/7'))
 line(305,y,335,y);resistor(335,y,'R'+str(base+4),'100');line(379,y,490,y);cap(399,y,'C'+str(base+2),'1nF');label(447,y+12,'AD7606');label(447,y-17,'V'+str(ch+1)+' / pin '+str(49+2*ch))
 line(18,y,18,143);resistor(18,143,'R'+str(base+1),'1M');line(62,143,80,143);label(83,140,'VMID')
 line(92,y,92,128);line(92,128,171,128);line(171,128,171,148);box(d,142,148,82,35,'D'+str(10+ch)+' BAV199')
 label(232,157,'pin 3 = RC'+str(ch)+'A');label(232,145,'pin 1 = GND; pin 2 = 3V0A')
 return d

def table(rows):
 n=len(rows[0]);widths=([110,175,214] if n==3 else [499/n]*n)
 t=Table([[para(c,'SmallX') for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#cadbd4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 return t

def markdown_story(source):
 lines=source.splitlines();out=[];i=0
 while i<len(lines):
  line=lines[i].strip()
  if not line:i+=1;continue
  if line.startswith('## '):
   out.extend([PageBreak(),para(line[3:],'H1X')]);i+=1;continue
  if line.startswith('### '):out.append(para(line[4:],'H2X'));i+=1;continue
  if line.startswith('!['):
   match=re.match(r'!\[(.*?)\]\(briefing-figures/(.*?).svg\)',line)
   if match:out.extend([figure(match[2]),para(match[1],'SmallX')])
   i+=1;continue
  if line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r'[: -]+',x) for x in cells):rows.append(cells)
    i+=1
   out.extend([table(rows),Spacer(1,12)]);continue
  if line.startswith('- '):out.append(para('• '+line[2:]));i+=1;continue
  words=[line];i+=1
  while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','- ')):
   words.append(lines[i].strip());i+=1
  out.append(para(' '.join(words)))
 return out

def build():
 assets=D/'briefing-figures';assets.mkdir(exist_ok=True)
 for name in ('architecture','filter','timing','power'):renderSVG.drawToFile(figure(name),str(assets/(name+'.svg')))
 source=(D/'understanding-the-recorder.md').read_text()
 toc=TableOfContents();toc.levelStyles=[ParagraphStyle(name='Contents',fontName='Helvetica',fontSize=10,leading=14,spaceBefore=2,textColor=INK)]
 story=[Spacer(1,35),para('UNDERSTANDING MY','H2X'),para('Muscle and motion recorder','CoverX'),Spacer(1,15),para('Muttakin Rahman','H1X'),para('Supervisor meeting and laboratory preparation'),figure('architecture'),Spacer(1,20),para('AD7606 / two MyoWare RAW channels / two ICM-42688-P carriers','H2X'),para('Expanded edition - 7 October 2026'),para('Engineering prototype. Design, software and simulation evidence are distinct from physical measurements, which remain pending.'),PageBreak(),para('Reading map','H1X'),para('Start with sections 1-3 and 20 for the meeting. Use the engineering chapters and staged workbook for implementation.'),toc]
 story+=markdown_story('## '+source.split('## ',1)[1])
 Document(D/'understanding-the-recorder.pdf','Understanding my muscle and motion recorder').multiBuild(story)
 css='body{background:#edf0ed;color:#172c29;font:17px/1.65 system-ui;margin:0}main{max-width:960px;margin:30px auto;padding:40px;background:white;border-top:6px solid #096b60}h1,h2,h3,a{color:#096b60}h2{margin-top:45px}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #cadbd4;padding:10px;vertical-align:top;text-align:left}th{background:#e8f2ee}nav{display:flex;gap:20px;flex-wrap:wrap}code{overflow-wrap:anywhere} @media(max-width:700px){main{padding:20px;margin:0}table{display:block;overflow:auto}}'
 (D/'understanding-the-recorder.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Understanding my recorder</title><style>'+css+'</style></head><body><main><nav><a href="../development/index.html">Build sequence</a><a href="understanding-the-recorder.pdf">Handbook PDF</a><a href="circuit-diagrams.pdf">Circuit diagrams</a><a href="../viewer/build.html">Assembly workspace</a></nav>'+md.render(source)+'</main></body></html>')
 with tempfile.TemporaryDirectory() as tmp:
  tmp=Path(tmp);sch=P/'hardware/main/afo_revb_main.kicad_sch'
  subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','sch','export','pdf','--output',str(tmp/'schematic.pdf'),str(sch)],check=True)
  circuit=[para('Circuit diagrams','CoverX'),para('AD7606 / fixed two EMG channels / ICM-42688-P','H1X'),para('Muttakin Rahman | 7 October 2026'),para('This pack combines a functional bench interface map with the exact KiCad recorder schematic. The final sheet retains its original large vector page: zoom to read component values, pin numbers and nets. It is not an A4 wiring poster.'),figure('architecture'),para('How to use this pack','H2X'),para('Use the next page to identify signals. Use the assembly workspace and contact-level wiring tables for physical module header positions. Use the final KiCad sheet for the custom PCB circuit, passive components, protection, decoupling and connector numbering.'),para('The bench uses an ESP32 DevKit and regulator / ADC / IMU modules; the custom PCB uses the ESP32 module and ADC chip directly. GPIO identity is not the same as package pad number or DevKit header position. SD CMD differs between the two firmware profiles.'),para('Engineering prototype. Physical module straps, voltage levels and reference must be measured before connecting ESP32 signal pins. No hardware performance or human-use safety is certified by this drawing.'),PageBreak(),para('Bench interface map','H1X'),table([['Function','ESP32 GPIO / rail','Destination / condition'],['ADC supply','Regulated 5 V / GND','AD7606 module power; VIO separately at 3.3 V'],['Conversion trigger','GPIO11','CVA and CVB together'],['ADC status / reset','GPIO8 / GPIO9','BUSY / RST'],['ADC serial control','GPIO10 / GPIO12','CS / RD-SCLK'],['ADC data','GPIO13','DOUTA (DB7 in serial mode); 128 clocks for eight words'],['ADC static settings','Defined straps','Serial mode; +/-5 V; oversampling off. Verify module strap location.'],['EMG1 / EMG2','3.0 V analog, GND, RAW','Two matching buffered two-pole RC paths to V1 / V2; V3-V8 defined at ground'],['IMU shared SPI','GPIO4 / 5 / 6','MOSI / MISO / SCLK'],['Foot IMU','GPIO7 / GPIO16','CS / interrupt; 3.3 V and ground'],['Shank IMU','GPIO15 / GPIO17','CS / interrupt; 3.3 V and ground'],['microSD','GPIO39 / 40 / 47','Bench CLK / D0 / CMD; PCB CMD uses GPIO38'],['Controls','GPIO18 / 21','Button / active-low USB-present detection'],['Indicators / battery','GPIO41 / 42 / 2; GPIO1','Record / error / low LEDs; battery-divider sense']]),para('Connector reference','H2X'),para('PCB J3/J4: 1=3.3 V, 2=GND, 3=SCLK, 4=MOSI, 5=MISO, 6=CS, 7=INT, 8=GND. J5/J6: 1=3.0 V analog, 2=GND, 3=RAW. These are recorder connector numbers, not the external carrier header numbering.'),para('Source: hardware/main/afo_revb_main.kicad_sch; schematic SHA-256: '+hashlib.sha256(sch.read_bytes()).hexdigest(),'SmallX')]
  circuit.extend([PageBreak(),para('Two EMG input circuits','H1X'),para('Electrical reading diagram derived from circuit-spec.json. Named nets join the same electrical node. Component references and amplifier pins below are the PCB references; breadboard DIP packages use their own contact tables.'),analog_channel(0),analog_channel(1),para('Supply and unused amplifiers','H2X'),para('U3 and U4: pin 4 = 3V0A, pin 11 = GND, each with 100 nF local bypass (C33/C34). Unused sections: pin 10 = GND, pins 9/8 joined; pin 12 = GND, pins 13/14 joined. J5/J6 pin 1 = 3V0A and pin 2 = GND. All filter capacitors return to the common ground.'),para('The clamp diagram states the BAV199 pin connections explicitly; it does not establish protection performance. Use the selected package pinout and polarity. Confirm the received AD7606 module pin map before wiring.'),PageBreak(),para('Midpoint and ADC connections','H1X'),para('Midpoint circuit','H2X'),table([['Element','Connection','Purpose'],['R40 / R41: 10k each','3V0A -> R40 -> VMID_DIV -> R41 -> GND','Nominal half-supply divider'],['C30: 1 uF','VMID_DIV to GND','Divider filtering'],['U5 MCP6001','Pin 3 VMID_DIV; pins 4 and 1 VMID_BUF; pin 5 3V0A; pin 2 GND','Unity-gain midpoint buffer'],['R42: 100 / C31: 1 uF','VMID_BUF -> R42 -> VMID; C31 VMID to GND','Reference isolation and filtering'],['C32: 100 nF','3V0A to GND at U5','Local supply bypass'],['R101 / R111: 1M','RAW0 / RAW1 to VMID','Defined bias with sensor unplugged']]),para('AD7606 chip static connections','H2X'),table([['Signal','Chip pin / connection','Interpretation'],['AVCC / VDRIVE','1,37,38,48: 5V_ADC; 23: 3V3D','Analog supply and interface voltage are separate'],['PAR/SER / STBY / RANGE','6: 3V3D; 7: 3V3D; 8: GND','Serial operation, normal operation, +/-5 V'],['OS0 / OS1 / OS2','3,4,5: GND','Oversampling disabled'],['CONVST A / B','9,10: ADC_CONVST','Simultaneous trigger'],['RST / RD / CS / BUSY','11 / 12 / 13 / 14','Reset / SCLK / chip select / conversion status'],['DOUTA / DOUTB','24: ADC_MISO; 25 unused','Single-output eight-word read'],['Reference select','34: 3V3D','Internal reference enabled'],['Analog input pair','49: AIN0P; 51: AIN1P; 50,52 GND','Two retained channels'],['Other analog inputs','53-64: GND','Unused input and return pins defined']]),para('See the following original KiCad sheet for reference capacitors, both REGCAP nodes, supply bypassing, every remaining digital pin, switching regulators, USB, SD, buttons and indicators. This summary supplements that sheet; it is not a replacement for its complete netlist.','SmallX')])
  Document(tmp/'intro.pdf','Circuit diagrams - AD7606 two-channel ICM').build(circuit)
  writer=PdfWriter()
  for file in (tmp/'intro.pdf',tmp/'schematic.pdf'):writer.append(str(file))
  writer.add_metadata({'/Title':'Circuit diagrams - AD7606 two-channel ICM-42688-P','/Author':'Muttakin Rahman'})
  with (D/'circuit-diagrams.pdf').open('wb') as f:writer.write(f)
 print({name:len(PdfReader(D/name).pages) for name in ('understanding-the-recorder.pdf','circuit-diagrams.pdf')})
if __name__=='__main__':build()
