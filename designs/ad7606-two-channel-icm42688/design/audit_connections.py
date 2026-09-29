#!/usr/bin/env python3
"""Fresh KiCad checks and direct PCB-pad comparison (requires KiCad's pcbnew Python)."""
import json,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew
P=Path(__file__).resolve().parents[1];O=P/'docs/refinement-checks';O.mkdir(exist_ok=True)
K=os.environ.get('KICAD_CLI','/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
result={'hardware_measured':False,'checks':{},'errors':[]}
for kind,cmd,ext in [('erc',['sch','erc'],'kicad_sch'),('drc',['pcb','drc'],'kicad_pcb')]:
 r=subprocess.run([K,*cmd,'--format','json','--output',str(O/(kind+'.json')),str(P/'hardware/main'/('afo_revb_main.'+ext))],capture_output=True,text=True)
 (O/(kind+'.log')).write_text(r.stdout+r.stderr);r.check_returncode()
 d=json.loads((O/(kind+'.json')).read_text());bad=d.get('violations',[])+d.get('unconnected_items',[])+[v for s in d.get('sheets',[]) for v in s.get('violations',[])]
 result['checks'][kind]={'violations':len(bad)}
 if bad:result['errors'].append([kind,bad])
subprocess.run([K,'sch','export','netlist','--format','kicadxml','--output',str(O/'netlist.xml'),str(P/'hardware/main/afo_revb_main.kicad_sch')],check=True,capture_output=True)
nets={}
for n in ET.parse(O/'netlist.xml').findall('.//nets/net'):
 for e in n.findall('node'):nets[e.get('ref'),e.get('pin')]=n.get('name').lstrip('/')
board=pcbnew.LoadBoard(str(P/'hardware/main/afo_revb_main.kicad_pcb'))
pads={}
for fp in board.GetFootprints():
 for pad in fp.Pads():pads.setdefault((fp.GetReference(),pad.GetNumber()),set()).add(pad.GetNetname().lstrip('/'))
spec=json.loads((P/'design/circuit-spec.json').read_text());count=0
for part in spec['parts']:
 for pin,net in part['pins'].items():
  if net is None:continue
  count+=1;k=(part['ref'],pin)
  if nets.get(k)!=net:result['errors'].append(['schematic',*k,net,nets.get(k)])
  if pads.get(k)!={net}:result['errors'].append(['actual PCB pad',*k,net,sorted(pads.get(k,[]))])
result['checks']['direct_schematic_and_pcb_pins']=count
# Independently transcribed ESP32-S3-WROOM-1 pad/GPIO map; compiler handles profile #if.
module={4:4,5:5,6:6,7:7,8:15,9:16,10:17,11:18,12:8,17:9,18:10,19:11,20:12,21:13,23:21,31:38,32:39,33:40,34:41,35:42,38:2,39:1}
expected={'ADC_CS':10,'ADC_CONVST':11,'ADC_RESET':9,'ADC_DRDY':8,'ADC_SCK':12,'ADC_MISO':13,'IMU_MOSI':4,'IMU_MISO':5,'IMU_SCK':6,'FOOT_CS':7,'SHANK_CS':15,'FOOT_INT':16,'SHANK_INT':17,'SD_CLK':39,'SD_D0':40,'USB_PRESENT_PIN':21,'BUTTON_PIN':18,'LED_RECORD':41,'LED_ERROR':42,'LED_BATTERY':2,'BATTERY_PIN':1}
alias={'SD_CLK':'SD_CLK_MCU','USB_PRESENT_PIN':'USB_PRESENT_N','BUTTON_PIN':'BUTTON','LED_RECORD':'LED_REC','LED_ERROR':'LED_ERR','LED_BATTERY':'LED_LOW','BATTERY_PIN':'BAT_SENSE'}
for profile in ['pcb','breadboard']:
 flags=['-DAFO_AD7606=1','-DEMG_CHANNEL_COUNT=2']+(['-DAFO_BREADBOARD=1'] if profile=='breadboard' else [])
 r=subprocess.run(['cc','-E','-dM','-x','c',*flags,str(P/'firmware/main/board.h')],capture_output=True,text=True);r.check_returncode()
 macros=dict(re.findall(r'^#define\s+(\w+)\s+(\d+)\b',r.stdout,re.M))
 values=dict(expected,SD_CMD=47 if profile=='breadboard' else 38)
 for name,gpio in values.items():
  if int(macros.get(name,-1))!=gpio:result['errors'].append(['firmware GPIO',profile,name,macros.get(name),gpio])
  if profile=='pcb':
   pad=next(str(p) for p,g in module.items() if g==gpio)
   if nets.get(('U1',pad))!=alias.get(name,name):result['errors'].append(['GPIO to module',name,pad])
 result['checks'][profile+'_firmware_gpio_count']=len(values)
result['status']='FAIL' if result['errors'] else 'PASS'
(O/'connectivity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(bool(result['errors']))
