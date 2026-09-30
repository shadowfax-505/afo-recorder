#!/usr/bin/env python3
"""Run integrated Wokwi cases and validate actual saved bytes and UDP packets."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor,as_completed

P=Path(__file__).resolve().parent
ROOT=P.parent.parent
sys.path.insert(0,str(ROOT/'host'))
from afo_format import HEADER_SIZE,RECORD_SIZE,decode_record,decode_emg_b,decode_fifo,IMU,make_header,read_header
from convert import convert
from live_protocol import decode_packet,encode_packet
from live_receiver import Capture

CASES={
    'normal':(0,0), 'write-delay-50ms':(1,0), 'queue-stall-350ms':(2,2),
    'storage-write-error':(3,1), 'usb-attached-during-recording':(4,7),
    'battery-low':(5,4), 'adc-stuck-busy':(6,6), 'imu-fifo-overflow':(7,3),
    'imu-missing-interrupt':(8,3), 'no-wireless-subscriber':(9,0),
    'wireless-packet-loss':(10,0), 'interrupted-recording':(11,None),
    'storage-mount-failure':(12,None), 'full-card-refusal':(13,None),
    'filtered-synthetic-emg':(14,0), 'absent-shank':(15,None),
    'adc-busy-stays-low':(6,6), 'adc-trigger-ignored':(6,6),
}

def make_diagram(case):
    number,_=CASES[case]
    diagram=json.loads((P/'diagram.json').read_text())
    by_id={part['id']:part for part in diagram['parts']}
    by_id['fixture']['attrs']['case']=str(number)
    if number==6:by_id['adc']['attrs']['fault']='1'
    if case=='adc-busy-stays-low':by_id['adc']['attrs']['fault']='4'
    if case=='adc-trigger-ignored':by_id['adc']['attrs']['fault']='5'
    if number==7:by_id['foot']['attrs']['fault']='2'
    if number==8:by_id['foot']['attrs']['fault']='3'
    if number==15:by_id['shank']['attrs']['fault']='1'
    if number==14:by_id['adc']['attrs']['waveform']='1'
    return diagram

def extract(text,kind):
    """Require contiguous offsets and an exact end size; never accept partial output."""
    matches=re.findall(rf'^EXPORT,{kind},(\d+),([A-Za-z0-9+/=]*)\r?$',text,re.M)
    end=re.findall(rf'^EXPORT_END,{kind},(\d+)\r?$',text,re.M)
    if len(end)!=1:raise ValueError(f'{kind}: missing or duplicate export terminator')
    result=bytearray()
    for offset,data in matches:
        if int(offset)!=len(result):raise ValueError(f'{kind}: noncontiguous offset')
        result.extend(base64.b64decode(data,validate=True))
    if int(end[0])!=len(result):raise ValueError(f'{kind}: incomplete export')
    return bytes(result)

def packet_list(data):
    packets=[];offset=0
    while offset<len(data):
        if offset+2>len(data):raise ValueError('truncated UDP length')
        length=struct.unpack_from('<H',data,offset)[0];offset+=2
        if offset+length>len(data):raise ValueError('truncated UDP payload')
        packet=data[offset:offset+length];decode_packet(packet)
        packets.append(packet);offset+=length
    return packets

def assess(case,text,out):
    number,expected=CASES[case]
    if re.search(r'assert failed:|Guru Meditation|abort\(\)|Stack canary|INTEGRATED_FAILURE',text):
        raise ValueError('firmware assertion, panic or fixture failure')
    if len(re.findall(rf'^INTEGRATED_COMPLETE,case={number},',text,re.M))!=1:
        raise ValueError('missing or duplicated completion marker')
    if number in (12,13,15):
        if 'refused=true' not in text or 'EXPORT,AFO,' in text:raise ValueError('failed start was not refused')
        expected_log='Start refused:' if number==13 else 'Initialization failed; recording disabled.'
        if expected_log not in text:raise ValueError('missing explicit production refusal')
        return {'pass':True,'refused':True,'reason':expected_log}
    line=re.findall(r'^INTEGRATED_RESULT,([^\r\n]+)',text,re.M)
    if len(line)!=1:raise ValueError('missing/duplicate production result')
    counters={key:int(value) for key,value in (x.split('=') for x in line[0].split(','))}
    if counters['case']!=number:raise ValueError('wrong test case')
    failures=[]
    if expected is not None and counters['fault']!=expected:
        failures.append(f'expected stop {expected}, got {counters["fault"]}')
    raw=extract(text,'AFO');wire=extract(text,'UDP')
    # Keep exact unmodified production output separate. Derived fixtures identify simulation.
    (out/'recorder-output.raw').write_bytes(raw)
    original=read_header(io.BytesIO(raw));metadata=dict(original,synthetic=True,simulation='Wokwi integrated recorder')
    tagged=make_header(metadata)+raw[HEADER_SIZE:]
    source=out/'simulated-recording.afolog';source.write_bytes(tagged)
    quality=convert(source,out/'converted',make_plots=(number==14))
    records=[decode_record(raw[i:i+RECORD_SIZE]) for i in range(HEADER_SIZE,len(raw),RECORD_SIZE)]
    emg=[r for r in records if r.kind==7]
    if case in ('adc-busy-stays-low','adc-trigger-ignored') and (emg or not counters['adc_errors']):
        failures.append('unconfirmed conversion accepted plausible EMG data')
    ends=[r for r in records if r.kind==5]
    stimulus=None
    if number==14:
        import csv
        with (P/'stimulus/filtered-samples.csv').open() as file:
            stimulus=[(int(row['code1']),int(row['code2'])) for row in csv.DictReader(file)]
    for record in emg:
        codes,*_=decode_emg_b(record,original)
        target=stimulus[(record.sequence-1)%len(stimulus)] if stimulus is not None else (6554,13107)
        if tuple(codes)!=target:raise ValueError(f'ADC code/channel mismatch: {codes}')
    for identity,kind in ((1,2),(2,3)):
        for r in records:
            if r.kind==kind:
                packet,*_=IMU.unpack(r.payload);axes=decode_fifo(packet)
                if axes['ax']!=identity or axes['az']!=2048:raise ValueError('IMU identity/axis mismatch')
    if expected==0:
        if not quality['no_detected_sample_loss'] or not quality['signal_checks_pass']:
            failures.append('normal recording has a quality failure')
        if len(emg)<7920 or not 7920<=quality['emg_rate_from_host_timestamps_hz']<=8080:
            failures.append('normal recording did not sustain modeled 8 kHz')
    elif number==11:
        if quality['session_finalized'] or not any(x['kind']=='missing_end' for x in quality['issues']):
            failures.append('interrupted recording looks finalized')
    elif expected==1:
        if quality['no_detected_sample_loss']:failures.append('storage fault appears loss-free')
    else:
        if len(ends)!=1 or ends[0].flags!=expected or quality['no_detected_sample_loss']:
            failures.append('fault did not produce explicit abnormal recording')
    packets=packet_list(wire)
    capture=Capture(out/'live-capture')
    try:
        for index,packet in enumerate(packets):
            p=decode_packet(packet)
            if p['kind']==1 and p['session']:
                m=dict(p['metadata'],synthetic=True)
                packet=encode_packet(1,p['boot'],p['session'],p['sequence'],
                    json.dumps(m,separators=(',',':')).encode(),dropped=p['dropped'])
            capture.accept(packet,now=index*.001)
        live=capture.snapshot()
    finally:capture.close()
    (out/'udp-output.raw').write_bytes(wire)
    live={k:v for k,v in live.items() if k not in ('emg','output','packet_age_s','data_age_s')}
    (out/'live-results.json').write_text(json.dumps(live,indent=2)+'\n')
    if live['stats']['invalid_packets'] or live['stats']['unknown_session_packets']:
        raise ValueError('production UDP framing/session decode failed')
    if number==9:
        if packets:raise ValueError('packets without subscriber')
    elif number==11:
        if live.get('ended'):raise ValueError('interrupted session live view reports normal end')
    elif number==10:
        if not counters['discarded'] or not live['stats']['packet_gaps']:
            raise ValueError('injected UDP gaps were hidden')
        # END is also best-effort: losing it must not fabricate a clean stop.
        if live.get('ended'):
            if live.get('stop_reason')!=0:raise ValueError('wrong received END reason')
        elif live.get('stop_reason') is not None:
            raise ValueError('wireless ending was invented without END')
        if not quality['no_detected_sample_loss']:
            raise ValueError('wireless packet loss affected the saved stream')
        if live['metadata']['active_channel_count']!=2:raise ValueError('wrong live channel count')
    else:
        if not live.get('ended') or live.get('stop_reason')!=expected:
            failures.append('live view missed or misreported stop reason')
        if expected==0 and set(live.get('imu',{}))!={'foot','shank'}:raise ValueError('live view missing IMU identity')
        if live['metadata']['active_channel_count']!=2:raise ValueError('wrong live channel count')
    return {'pass':not failures,'failures':failures,'production':counters,'saved_record_count':len(records),'saved_bytes':len(raw),
            'quality':quality,'live':live,'udp_packets':len(packets),
            'source_sha256':hashlib.sha256(raw).hexdigest()}

def run_case(case,out,timeout=300,execute=subprocess.run):
    out.mkdir(parents=True,exist_ok=False)
    diagram=out/'diagram.json';diagram.write_text(json.dumps(make_diagram(case),indent=2)+'\n')
    serial=out/'serial.txt'
    cmd=[os.environ.get('WOKWI_CLI','wokwi-cli'),str(P),'--diagram-file',str(diagram.resolve()),
         '--timeout','120000','--expect-text',f'INTEGRATED_COMPLETE,case={CASES[case][0]},',
         '--fail-text','assert failed:','--serial-log-file',str(serial.resolve())]
    result={'case':case,'pass':False}
    try:
        manifest=json.loads((P/'firmware/manifest.json').read_text())
        for name,digest in manifest['sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('image or source changed since build: '+name)
        (out/'tested-build.json').write_text(json.dumps(manifest,indent=2)+'\n')
        with (out/'cli.txt').open('w') as log:
            process=execute(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        result['exit_code']=process.returncode
        if 'monthly CI minute quota' in (out/'cli.txt').read_text():
            result.update(status='not_run_quota',pass_=None,error='Wokwi monthly CI quota exhausted')
            result['pass']=None;result.pop('pass_')
            (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
            return result
        result.update(assess(case,serial.read_text(),out))
        if process.returncode:
            result['firmware_checks_pass']=result['pass'];result['pass']=False
            result['error']='Wokwi CLI transport/execution exit '+str(process.returncode)
    except (ValueError,KeyError,OSError,subprocess.TimeoutExpired) as error:
        result['error']=type(error).__name__+': '+str(error)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=list(CASES),action='append')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--jobs',type=int,default=1,choices=range(1,5))
    args=parser.parse_args()
    if not os.environ.get('WOKWI_CLI_TOKEN'):raise SystemExit('Configure WOKWI_CLI_TOKEN privately; no pass is claimed.')
    (P/'results').mkdir(exist_ok=True)
    root=args.out or Path(tempfile.mkdtemp(prefix='run-',dir=P/'results'))
    root.mkdir(parents=True,exist_ok=True)
    results=[]
    def execute(case):
        print('Running '+case,flush=True)
        result=run_case(case,root/case,timeout=900)
        print(json.dumps({'case':case,'pass':result['pass'],'error':result.get('error'),
            'failures':result.get('failures')}),flush=True)
        return result
    cases=args.case or list(CASES)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures={pool.submit(execute,case):case for case in cases}
        results=[f.result() for f in as_completed(futures)]
    results.sort(key=lambda r:cases.index(r['case']))
    summary={'engine':'Wokwi ESP32-S3 with real ESP-IDF FreeRTOS, FatFS and lwIP',
             'hardware_measured':False,'physical_acceptance_pass':False,
             'substitutions':['SDMMC replaced by sparse PSRAM disk','Battery/controls replaced by fixture values',
                              'Laptop radio link replaced by MCU UDP loopback subscriber'],
             'cases_passed':sum(x['pass'] is True for x in results),'cases':results}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all(x['pass'] for x in results) else 1

if __name__=='__main__':raise SystemExit(main())
