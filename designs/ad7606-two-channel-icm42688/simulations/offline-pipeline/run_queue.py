#!/usr/bin/env python3
"""Long-duration event-count queue model, not hardware endurance testing."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
cases=[('one-hour-normal',3600,2097152,0,10,0),
       ('one-hour-50ms-stalls',3600,2097152,50,10,0),
       ('one-hour-180ms-stalls',3600,2097152,180,10,0),
       ('one-hour-220ms-stalls',3600,2097152,220,30,0),
       ('350ms-overflow',10,2097152,350,1,2),
       ('insufficient-throughput',60,500000,0,10,2)]
with tempfile.TemporaryDirectory(prefix='afo-queue-model-') as name:
    binary=Path(name)/'queue'
    subprocess.run([os.environ.get('CC','cc'),'-std=c11','-O2','-Wall','-Wextra','-Werror',
        str(P/'queue_budget.c'),'-o',str(binary)],check=True)
    results=[]
    for label,duration,speed,stall,period,expected in cases:
        completed=subprocess.run([str(binary),str(duration),str(speed),str(stall),str(period)],
            capture_output=True,text=True,check=True,timeout=60)
        result=json.loads(completed.stdout);assert result['stop_reason']==expected
        result.update(case=label);result['pass']=True
        if expected==0:
            assert result['produced'][0]==duration*8000 and result['queue_high_water']<2048
        else:assert result['queue_high_water']==2048
        results.append(result);print(label+' PASS')
report={'engine':'native event-count queue model, configured 8kHz/200Hz and 128-record writes',
    'hardware_measured':False,'firmware_executed':False,'cases_passed':len(results),
    'queue_time_budget_ms':2048/(8000+400)*1000,'record_bytes_s':(8000+400)*64,
    'two_hour_nominal_bytes_with_status_and_header':(8000+400)*64*7200+7200*64+4096+64,
    'source_sha256':hashlib.sha256((P/'queue_budget.c').read_bytes()).hexdigest(),
    'limits':['Modeled write throughput and latencies are assumptions, not SD-card measurements',
        'Arrival/write counts only; no binary files, firmware, GPIO, scheduler or persistence',
        'Cannot qualify one-hour recording or two-hour battery runtime'], 'cases':results}
(P/'results').mkdir(exist_ok=True)
(P/'results/queue-budget.json').write_text(json.dumps(report,indent=2)+'\n')
