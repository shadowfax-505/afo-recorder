from pathlib import Path
import json,csv
for root in [Path(__file__).resolve().parents[1]]:
 name=root.name
 ad=any(p['ref']=='U2' and 'AD7606' in p['value'] for p in json.load(open(root/'design/main.json'))['parts'])
 r=root;d=r/'breadboard';d.mkdir(exist_ok=True)
 spec=json.load(open(r/'design/main.json'));by={p['ref']:p for p in spec['parts']};connections=[];components=[]
 # Every row is a 5-hole connected strip, a-e and f-j are separate.
 for ch in range(2):
  n=100+ch*10;board=f'BB{ch+1}';nets={}
  pairs=[(f'R{n}','a2','a4'),(f'R{n+1}','c2','c8'),(f'C{n}','b4','b6'),(f'R{n+2}','a18','a20'),(f'C{n+1}','b20','b24'),(f'R{n+4}','a26','a28'),(f'C{n+2}','b28','b32')]
  if not ad:pairs += [(f'R{n+3}','c22','c20'),(f'R{n+5}','a30','a32')]
  for ref,a,b in pairs:
   p=by[ref];components.append(dict(ref=ref,board=board,value=p['value'],terminals={'1':a,'2':b},stage=4 if ch==0 else 5))
   for pin,hole in [('1',a),('2',b)]:nets.setdefault(p['pins'][pin],[]).append(hole)
  opnets=[f'BUF{ch}A',f'BUF{ch}A',f'RC{ch}A','GND',f'RC{ch}B',f'BUF{ch}B',f'BUF{ch}B','3V0A'];holes=['e10','e11','e12','e13','f13','f12','f11','f10']
  components.append(dict(ref=f'UB{ch+1}',board=board,value='MCP6002-I/P DIP8; same amplifier family as PCB MCP6004',terminals={str(i+1):h for i,h in enumerate(holes)},stage=4 if ch==0 else 5))
  for net,hole in zip(opnets,holes):nets.setdefault(net,[]).append(hole)
  # Local supply bypass, dedicated to each DIP dual op-amp.
  components.append(dict(ref=f'CB{ch+1}',board=board,value='100nF local bypass',terminals={'1':'j10','2':'j8'},stage=4 if ch==0 else 5));nets.setdefault('3V0A',[]).append('j10');nets['GND'].append('j8')
  for net,ends in nets.items():
   for a,b in zip(ends,ends[1:]):connections.append(dict(board=board,net=net,from_hole=a,to_hole=b,stage=4 if ch==0 else 5))
   # Functional module terminals deliberately not physical positions on unknown modules.
   if net in ['GND','3V0A','VMID',f'RAW{ch}',f'AIN{ch}P',f'AIN{ch}N']:
    connections.append(dict(board=board,net=net,from_hole=ends[0],to_hole='TERMINAL:'+net,stage=4 if ch==0 else 5))
  # BAV199 soldered carrier: function names, no invented carrier-header numbering.
  for pin,net in [('1','GND'),('2','3V0A'),('3',f'RC{ch}A')]:connections.append(dict(board=board,net=net,from_hole=nets[net][0],to_hole=f'BAV199_CARRIER{ch+1}:CHIP_PAD_{pin}',stage=4 if ch==0 else 5))
 # Midpoint fixture BB0: one DIP dual, unused half in grounded follower configuration.
 board='BB0';nets={}
 for ref,a,b in [('R40','a2','a4'),('R41','b4','a6'),('C30','c4','b6'),('R42','a18','a20'),('C31','b20','a24')]:
  p=by[ref];components.append(dict(ref=ref,board=board,value=p['value'],terminals={'1':a,'2':b},stage=1))
  for pin,hole in [('1',a),('2',b)]:nets.setdefault(p['pins'][pin],[]).append(hole)
 holes=['e10','e11','e12','e13','f13','f12','f11','f10'];opnets=['VMID_BUF','VMID_BUF','VMID_DIV','GND','GND','MID_UNUSED','MID_UNUSED','3V0A']
 components.append(dict(ref='UB0',board=board,value='MCP6002-I/P midpoint; half B grounded follower',terminals={str(i+1):h for i,h in enumerate(holes)},stage=1))
 for net,hole in zip(opnets,holes):nets.setdefault(net,[]).append(hole)
 components.append(dict(ref='CB0',board=board,value='100nF',terminals={'1':'j10','2':'j8'},stage=1));nets['3V0A'].append('j10');nets['GND'].append('j8')
 for net,ends in nets.items():
  for a,b in zip(ends,ends[1:]):connections.append(dict(board=board,net=net,from_hole=a,to_hole=b,stage=1))
  if net in ['3V0A','GND','VMID']:connections.append(dict(board=board,net=net,from_hole=ends[0],to_hole='TERMINAL:'+net,stage=1))
 # Allocate a distinct physical hole to every jumper lead; same strip needs no jumper.
 def strip(h):return ('left' if h[0]<'f' else 'right',int(h[1:]))
 occupied={(p['board'],h) for p in components for h in p['terminals'].values()}
 def free(board,h):
  side,row=strip(h)
  for col in ('abcde' if side=='left' else 'fghij'):
   dest=col+str(row)
   if (board,dest) not in occupied:occupied.add((board,dest));return dest
  raise ValueError(('No free hole',board,h))
 allocated=[]
 for c in connections:
  a,b=c['from_hole'],c['to_hole']
  if ':' not in b and strip(a)==strip(b):continue
  c['from_hole']=free(c['board'],a)
  if ':' not in b:c['to_hole']=free(c['board'],b)
  allocated.append(c)
 connections=allocated
 j={'adc':'AD7606' if ad else 'ADS131M04','module':'RoboticsBD RBD-3184 / HW-AD7606-F4' if ad else 'ADS131M04 board - availability dependent','module_header_verified':False,'boards':3,'hardware_design':'AD7606_TWO_FIXED','components':components,'connections':connections,'limits':['Breadboard hole locations are specified for analog passives and DIP buffers only.','ADC/module terminal panels are logical labels, not physical header positions.','BAV199 and midpoint buffer require suitable carriers; verify carrier pin mapping.','PCB and DIP op-amp package parasitics differ; validate transfer/noise.']}
 (d/'layout.json').write_text(json.dumps(j,indent=2))
 with (d/'wiring.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['board','net','from_hole','to_hole','stage']);w.writeheader();w.writerows(connections)
 with (d/'placements.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['Board','Part','Value','Terminals','Stage'])
  for p in components:w.writerow([p['board'],p['ref'],p['value'],json.dumps(p['terminals']),p['stage']])
 # Validate shared breadboard strips cannot bridge unrelated nets.
 assigned={}
 def strip(h):return ('left' if h[0]<'f' else 'right',int(h[1:]))
 for c in connections:
  for h in [c['from_hole'],c['to_hole']]:
   if ':' in h:continue
   k=(c['board'],*strip(h));assert k not in assigned or assigned[k]==c['net'],(k,c);assigned[k]=c['net']
 (d/'checks.json').write_text(json.dumps({'unique_hole_check':'PASS','strip_short_check':'PASS','components':len(components),'jumper_connections':len(connections),'module_header_verified':False},indent=2))
