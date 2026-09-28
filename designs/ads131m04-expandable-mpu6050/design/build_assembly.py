"""Generate an inspectable breadboard assembly contract from layout + circuit spec."""
from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parents[1]
bb=json.loads((ROOT/'breadboard/layout.json').read_text());spec={p['ref']:p for p in json.loads((ROOT/'design/main.json').read_text())['parts']}
cols='abcdefghij'
def strip(h):return ('L' if h[0]<'f' else 'R')+h[1:]
boards=[];count=0
for k in range(bb['boards']):
 bid=f'BB{k}';parts=[p for p in bb['components'] if p['board']==bid];wires=[c for c in bb['connections'] if c['board']==bid];holes={};nets={};expected={};steps=[];parent={}
 def find(a):
  parent.setdefault(a,a)
  if parent[a]!=a:parent[a]=find(parent[a])
  return parent[a]
 def union(a,b):parent[find(a)]=find(b)
 def add(h,net,owner):
  assert h[0] in cols and 1<=int(h[1:])<=33,h
  assert h not in holes,('double occupancy',bid,h,owner,holes.get(h))
  holes[h]=[owner];expected.setdefault(net,[]).append(strip(h))
  for c in ('abcde' if h[0]<'f' else 'fghij'):
   key=c+h[1:];assert key not in nets or nets[key]==net,('strip short',bid,key,net,nets.get(key));nets[key]=net
 for p in parts:
  if p['ref'].startswith('UB'):
   assert p['terminals']==dict(zip(map(str,range(1,9)),['e10','e11','e12','e13','f13','f12','f11','f10'])),('DIP orientation',bid)
   n=['VMID_BUF','VMID_BUF','VMID_DIV','GND','GND','MID_UNUSED','MID_UNUSED','3V0A'] if k==0 else [f'BUF{k-1}A',f'BUF{k-1}A',f'RC{k-1}A','GND',f'RC{k-1}B',f'BUF{k-1}B',f'BUF{k-1}B','3V0A']
   pn={str(i+1):v for i,v in enumerate(n)};orient='MCP6002 DIP-8: notch toward row 9; pin 1=e10, pins 1–4 down the left, pins 5–8 up the right. Do not rotate 180°.'
  elif p['ref'].startswith('CB'):pn={'1':'3V0A','2':'GND'};orient='100 nF non-polarized bypass; fit close to IC supply connections.'
  else:pn=spec[p['ref']]['pins'];orient='Resistor: non-polarized; bend leads to the specified holes.' if p['ref'].startswith('R') else 'Use a non-polarized capacitor of the specified value. Body/lead spacing must be checked against the actual purchased part.'
  pins=[dict(pin=pin,hole=h,net=pn[pin]) for pin,h in p['terminals'].items()]
  for pin in pins:add(pin['hole'],pin['net'],p['ref']+'.'+pin['pin'])
  steps.append(dict(id=bid+'-'+p['ref'],kind='component',ref=p['ref'],title=p['ref']+' · '+p['value'],holes=list(p['terminals'].values()),pins=pins,orientation=orient,instruction='Insert '+p['ref']+': '+', '.join('pin '+x['pin']+' → '+x['hole']+' ('+x['net']+')' for x in pins)+'.'))
 # Short internal jumpers first; external module/carry leads are explicitly unresolved.
 wires=sorted(wires,key=lambda w:':' in w['to_hole'])
 for i,w in enumerate(wires):
  a,b,n=w['from_hole'],w['to_hole'],w['net'];external=':' in b;add(a,n,f'Jumper {i+1} end A')
  if not external:add(b,n,f'Jumper {i+1} end B');union(strip(a),strip(b))
  steps.append(dict(id=bid+'-wire-'+str(i+1),kind='external' if external else 'jumper',title=('External lead · ' if external else 'Jumper · ')+n,holes=[a] if external else [a,b],net=n,**{'from':a,'to':b},instruction=f'{a} → '+(f'{b} (logical endpoint only; physical pin pending verification).' if external else f'{b}. Both jumper ends must occupy these exact holes.')))
 # Every instance of a named local net must be connected through strips and jumpers.
 for net,nodes in expected.items():assert len({find(n) for n in nodes})==1,('open net',bid,net,nodes)
 boards.append(dict(id=bid,role='Midpoint reference' if k==0 else f'EMG{k} signal conditioning',stage=1 if k==0 else 4 if k==1 else 5,holes=holes,nets=nets,steps=steps))
 count+=len(holes)
scopes=['BB0 midpoint layout is specified. Regulated lab rails and dummy loads are external instruments; this does not reproduce the PCB switching regulator.', 'Controller physical header map is pending exact development-board SKU. Do not use approximate block coordinates as pins.', 'ADC module header / VIO / serial selection verification is required. This view does not release module wiring.', 'Build and inspect BB1, then perform synthetic-signal acceptance tests.', 'Build the remaining physical input paths one at a time; channel enable settings do not remove installed circuits.', 'Foot/shank ready-made IMU board SKU, pin ordering and orientation remain pending.', 'microSD module SKU/header pending. Follow functional firmware nets only after verifying the actual module.', 'Wi-Fi uses the ESP32 radio, not an added wired breadboard module. Check reception during SD recording.', 'Battery polarity, protection and final power circuitry require separate verification. No charger is included.', 'MyoWare RAW, supply and ground connections need a verified sensor connector/cable. Sensor outlines are not pin maps.']
a=dict(schema='afo-breadboard-assembly/2',variant=ROOT.name,title=bb['adc']+' · '+str(len(boards)-1)+' physical EMG inputs',pitch_mm=2.54,dip_row_spacing_mm=7.62,boards=boards,stage_scope=scopes,module_headers_verified=False)
(ROOT/'breadboard/assembly.json').write_text(json.dumps(a,indent=2)+'\n')
report=dict(status='PASS',boards=len(boards),occupied_holes_checked=count,checks=['unique lead hole occupancy','no different nets sharing a five-hole strip','all same-named local nets connected through strips and jumpers','passive pin nets from circuit specification','DIP-8 pin order and 7.62 mm row gap'],limits=['Does not establish physical external-module header pins','Component body geometry and jumper bends are illustrative','Does not validate all system power/controller/module circuits or physical performance'])
(ROOT/'breadboard/assembly-checks.json').write_text(json.dumps(report,indent=2)+'\n')
with (ROOT/'breadboard/assembly-steps.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Board','Step','Type','Part_or_net','Holes','Instruction','Orientation','External_header_verified'])
 for b in boards:
  for i,s in enumerate(b['steps'],1):w.writerow([b['id'],i,s['kind'],s['title'],'; '.join(s['holes']),s['instruction'],s.get('orientation',''),'NO' if s['kind']=='external' else 'not applicable'])
print(ROOT.name,json.dumps(report))
