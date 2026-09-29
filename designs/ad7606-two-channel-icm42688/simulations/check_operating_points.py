#!/usr/bin/env python3
"""ngspice DC/loading checks. Explicit surrogate, not device qualification."""
import csv,json
from pathlib import Path
from ngspice_runner import Spice
from run_analog import circuit
P=Path(__file__).resolve().parent
out=P/'results';out.mkdir(exist_ok=True)
sp=Spice();rows=[]
for source_r in [0,100,10000]:
 for voltage in [0,.02,.1,1,1.5,2,2.9,2.98,3]:
  net=circuit()
  for i in range(2):
   net=net.replace(f'Vin{i} raw{i} 0 DC 1.5 AC 1',f'Vin{i} src{i} 0 DC {voltage}\nRs{i} src{i} raw{i} {max(source_r,1e-6)}')
  sp.circuit(net);sp.command('op')
  raw=(voltage*1e6+1.5*source_r)/(1e6+source_r)
  predicted=min(max(raw,.02),2.98)/(1+101/1e6)
  for i in range(2):
   v=float(sp.vector(f'v(p{i})')[0]);assert abs(v-predicted)<1e-6,(v,predicted)
   rows.append([i+1,source_r,voltage,raw,v,predicted,round(v/5*32768)])
net=circuit()
for i in range(2):net=net.replace(f'Vin{i} raw{i} 0 DC 1.5 AC 1','* Sensor unplugged: 1Meg to midpoint remains')
(P/'analog_unplugged.cir').write_text(net);sp.circuit(net);sp.command('op')
unplugged=[float(sp.vector(f'v(p{i})')[0]) for i in range(2)]
assert all(abs(v-1.5/(1+101/1e6))<1e-6 for v in unplugged)
with (out/'dc-loading.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['channel','source_ohm','source_v','loaded_raw_v','adc_v','predicted_v','ideal_code']);w.writerows(rows)
# No clamp extrapolation: source sweep stays inside the intended 0..3V domain.
result={'engine':'ngspice','cases':len(rows),'pass':True,'unplugged_adc_v':unplugged,'headroom_model_v':[.02,2.98],
'limitations':['The assumed 20mV headroom is not a guaranteed MCP6004 limit.','No physical noise, diode current, startup, crosstalk or ADC reference error measured.','1Meg ADC load is an approximation; source impedances are test cases, not a MyoWare output model.']}
(out/'operating-points.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
