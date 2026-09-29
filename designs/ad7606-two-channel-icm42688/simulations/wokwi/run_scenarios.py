#!/usr/bin/env python3
"""Run actual ESP32 ELF in Wokwi CLI; no token is stored or printed."""
import json,os,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
EXPECTED={'normal':'WINDOW_COMPLETE','stuck-busy':'FAIL,ADC BUSY edge timeout','delayed-busy':'FAIL,ADC late conversion/read','incorrect-mode':'codes differ from known stimulus','absent-shank':'FAIL,IMU init/identity/readback','fifo-overflow':'FAIL,IMU FIFO/read','missed-interrupt':'FAIL,IMU missing interrupts/data'}
def assess(name,text):
 if name in ('normal','incorrect-mode'):
  matches=re.findall(r'ch1_mean=([-\d.]+).*ch2_mean=([-\d.]+)',text)
  known=bool(matches) and all(abs(float(a)-6554)<.01 and abs(float(b)-13107)<.01 for a,b in matches)
  if name=='incorrect-mode':return bool(matches) and not known
  return known and 'WINDOW_COMPLETE' in text and 'FAIL,' not in text and all(re.search(rf'IMU,{i},packets=[1-9]\d*,interrupts=[1-9]\d*,ax_raw={i+1},ay_raw=0,az_raw=2048,gx_raw=0,gy_raw=0,gz_raw=0',text) for i in (0,1))
 return EXPECTED[name] in text
if __name__=='__main__':
 if not os.environ.get('WOKWI_CLI_TOKEN'):raise SystemExit('WOKWI_CLI_TOKEN is not configured. No simulation pass is claimed. Configure it locally; do not commit it.')
 out=P/'results';out.mkdir(exist_ok=True);results=[]
 for name,expected in EXPECTED.items():
  cmd=[os.environ.get('WOKWI_CLI','wokwi-cli'),str(P),'--diagram-file',str(P/'scenarios'/f'{name}.json'),'--timeout','2500','--timeout-exit-code','0','--serial-log-file',str(out/f'{name}.serial.txt'),'--vcd-file',str(out/f'{name}.vcd')]
  try:
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
   (out/f'{name}.cli.txt').write_text(r.stdout+r.stderr)
   text=(out/f'{name}.serial.txt').read_text() if (out/f'{name}.serial.txt').exists() else ''
   passed=r.returncode==0 and assess(name,text) and (out/f'{name}.vcd').exists()
   results.append({'case':name,'expected':expected,'pass':passed,'exit_code':r.returncode})
  except subprocess.TimeoutExpired:results.append({'case':name,'expected':expected,'pass':False,'error':'wall-clock timeout'})
 (out/'scenarios.json').write_text(json.dumps({'engine':'Wokwi ESP32-S3','hardware_measured':False,'cases':results},indent=2)+'\n')
 raise SystemExit(not all(r['pass'] for r in results))
