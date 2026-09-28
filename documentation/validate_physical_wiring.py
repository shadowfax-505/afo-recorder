from pathlib import Path
import json,collections
R=Path(__file__).resolve().parent.parent;reports=[]
for p in (R/'designs').iterdir():
 if not p.is_dir():continue
 a=json.loads((p/'breadboard/assembly.json').read_text());d=json.loads((p/'breadboard/system-wiring.json').read_text());h=json.loads((p/'breadboard/physical-harness.json').read_text());gpio=json.loads((p/'design/breadboard-gpio-map.json').read_text())
 expected_sd={1:'3V3D',2:'GND',3:'SD_CLK',4:'SD_D0',5:'SD_CMD'}
 actual_sd={e['sd_pin']:w['net'] for w in d['connections'] for e in [w['a'],w['b']] if e['module']=='sd'}
 assert actual_sd==expected_sd,(p.name,'SD required contacts',actual_sd)
 for module in ['esp','adc','foot','shank']+['myo'+str(i) for i in range(1,a['emg_channel_paths']+1)]:
  nets={w['net'] for w in d['connections'] if any(e['module']==module for e in [w['a'],w['b']])}
  assert 'GND' in nets,(p.name,module,'missing ground')
  assert nets & {'3V3D','3V0A','5V'},(p.name,module,'missing supply')
 parent={};labels=collections.defaultdict(set);occupation={};degrees=collections.Counter();gchecks=0
 def find(x):
  parent.setdefault(x,x)
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 def join(x,y):parent[find(x)]=find(y)
 def strip(b,h):return (b,('L' if h[0]<'f' else 'R')+h[1:])
 def node(e):
  if e.get('hole'):return strip(e['module'],e['hole'])
  if e.get('header'):return (e['module'],e['header']+'.'+str(e['pin']))
  if e.get('sd_pin'):return (e['module'],'JP1.'+str(e['sd_pin']))
  if e.get('photo_pin'):return (e['module'],str((e['photo_pin']['x'],e['photo_pin']['z'])))
  if e.get('board_pin'):return (e['module'],str((e['board_pin']['x'],e['board_pin']['z'])))
  raise AssertionError(e)
 def norm(n):return {'5V_ADC':'5V','SD_CLK_MCU':'SD_CLK'}.get(n,n)
 def put(b,h,owner):
  assert 1<=int(h[1:])<=63 and h[0] in 'abcdefghij'
  assert (b,h) not in occupation,(p.name,b,h,occupation.get((b,h)),owner)
  occupation[b,h]=owner
 for b in a['boards']:
  for s in b['steps']:
   if s['kind']=='component':
    for pin in s['pins']:put(b['id'],pin['hole'],s['id']);labels[strip(b['id'],pin['hole'])].add(norm(pin['net']))
   elif s['kind']=='jumper':
    for hh in s['holes']:put(b['id'],hh,s['id']);labels[strip(b['id'],hh)].add(norm(s['net']))
    join(strip(b['id'],s['from']),strip(b['id'],s['to']))
 for w in h:
  for e in [w['a'],w['b']]:put(e['board'],e['hole'],w['id']);labels[strip(e['board'],e['hole'])].add(norm(w['net']))
  join(strip(w['a']['board'],w['a']['hole']),strip(w['b']['board'],w['b']['hole']))
 for w in d['connections']:
  for e in [w['a'],w['b']]:
   assert e['physical'],(p.name,e)
   if e.get('hole'):put(e['module'],e['hole'],w['id'])
   elif not w.get('local_solder'):degrees[node(e)]+=1
   labels[node(e)].add(norm(w['net']))
   if e['module']=='esp' and 'GPIO' in e['terminal']:
    g=e['terminal'].split('GPIO')[-1];assert norm(gpio[g])==norm(w['net']),(p.name,g,gpio[g],w['net']);gchecks+=1
  join(node(w['a']),node(w['b']))
 # Known copper inside the selected Adafruit 1230 adapter connects these pads.
 endpoints=[e for w in d['connections'] for e in [w['a'],w['b']] if e['module']=='ldo']
 for pad,header in [('U$1.1 solder pad','JP2.1'),('U$1.2 solder pad','JP2.2'),('U$1.6 solder pad','JP1.1')]:
  ee=next(e for e in endpoints if e['terminal']==pad)
  hh=next(e for e in endpoints if header in e['terminal'])
  join(node(ee),node(hh))
 roots=collections.defaultdict(set)
 for n,ns in labels.items():roots[find(n)].update(ns)
 conflicts={str(k):sorted(v) for k,v in roots.items() if len(v)>1};assert not conflicts,(p.name,conflicts)
 duplicates={str(k):v for k,v in degrees.items() if v>1};assert not duplicates,(p.name,duplicates)
 by_net=collections.defaultdict(set)
 for n,ns in labels.items():
  for net in ns:by_net[net].add(find(n))
 splits={net:len(rr) for net,rr in by_net.items() if len(rr)>1}
 assert not splits,(p.name,splits)
 reports.append(dict(disconnected_named_nets=0,design=p.name,holes_checked=len(occupation),wire_count=len(d['connections']),gpio_checks=gchecks,shorts=0,duplicate_holes=0,duplicate_connector_contacts=0,all_external_terminals_defined=True,hardware_tests=False))
(R/'documentation/physical-wiring-validation.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
