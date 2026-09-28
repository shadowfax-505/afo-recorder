from pathlib import Path
import json,re,xml.etree.ElementTree as E
for root in [Path(__file__).resolve().parents[1]]:
 r=root;name=r.name;s=json.load(open(r/'design/main.json'));v=json.load(open(r/'viewer/main.json'));parts={p['ref']:p for p in s['parts']};vp={p['ref']:p for p in v['parts']};errors=[]
 xml=E.parse(r/'hardware/main/netlist.xml');nets={}
 for n in xml.findall('.//nets/net'):
  for node in n.findall('node'):nets[(node.get('ref'),node.get('pin'))]=n.get('name').lstrip('/')
 inner=[t for t in v['tracks'] if t['layer']=='In1.Cu' and not t['via']]
 if inner:errors.append(['Signal tracks on reserved ground layer',len(inner)])
 checked=0
 for ref,p in parts.items():
  for pin,net in p['pins'].items():
   if not net:continue
   checked+=1
   if nets.get((ref,pin))!=net:errors.append(['schematic',ref,pin,net,nets.get((ref,pin))])
   pad=[a for a in vp[ref]['pads'] if a['pin']==pin]
   if not pad or any(a['net']!=net for a in pad):errors.append(['PCB/viewer pad',ref,pin,net,pad])
 # ESP32 module pad-to-GPIO mapping from module pinout. Check populated functional pads.
 pads={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,13:19,14:20,17:9,18:10,19:11,20:12,21:13,22:14,23:21,24:47,25:48,26:45,27:0,28:35,29:36,30:37,31:38,32:39,33:40,34:41,35:42,36:44,37:43,38:2,39:1}
 gpio=json.load(open(r/'design/gpio-map.json'))
 for pad,num in pads.items():
  if str(num) in gpio and parts['U1']['pins'].get(str(pad))!=gpio[str(num)]:errors.append(['GPIO net',num,pad])
 macros=dict(re.findall(r'^#define\s+(\w+)\s+(\d+)\b',(r/'firmware/main/board.h').read_text(),re.M));aliases={'USB_PRESENT_PIN':'USB_PRESENT_N','SD_CLK':'SD_CLK_MCU','BUTTON_PIN':'BUTTON','LED_RECORD':'LED_REC','LED_ERROR':'LED_ERR','LED_BATTERY':'LED_LOW','BATTERY_PIN':'BAT_SENSE'}
 for key,num in macros.items():
  net=aliases.get(key,key)
  if net in gpio.values() and gpio.get(num)!=net:errors.append(['firmware',key,num,net])
 bb=json.load(open(r/'breadboard/layout.json'));used=set()
 for p in bb['components']:
  if p['ref'] in parts and p['value']!=parts[p['ref']]['value']:errors.append(['breadboard value',p['ref']])
  for h in p['terminals'].values():
   k=p['board'],h
   if k in used:errors.append(['occupied component hole',k])
   used.add(k)
 for c in bb['connections']:
  for h in [c['from_hole'],c['to_hole']]:
   if ':' in h:continue
   k=c['board'],h
   if k in used:errors.append(['occupied jumper hole',k])
   used.add(k)
 for t in ['erc','drc']:
  report=json.load(open(r/'docs'/f'{t}.json'));bad=report.get('violations',[])+report.get('unconnected_items',[])+sum([sh.get('violations',[]) for sh in report.get('sheets',[])],[])
  if bad:errors.append([t,bad])
 result=dict(status='FAIL' if errors else 'PASS',checked_functional_pins=checked,errors=errors,scope='Schematic XML, actual PCB pad export, firmware GPIO map, breadboard values and hole occupancy. Not physical module header validation.',module_headers_verified=False)
 (r/'docs/consistency.json').write_text(json.dumps(result,indent=2));print(name,json.dumps(result))
