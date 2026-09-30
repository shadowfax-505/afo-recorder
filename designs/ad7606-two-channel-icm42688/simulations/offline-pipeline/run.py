#!/usr/bin/env python3
"""Offline analog-to-file co-simulation using real C drivers and serializer."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'host'))
from afo_format import read_header
from convert import convert

def run(duration_seconds=2, output=None, compact_directory=None):
    assert isinstance(duration_seconds, int) and 2<=duration_seconds<=3600
    sample_count=8000*duration_seconds
    result=Path(output) if output else P/'results'
    result.mkdir(parents=True,exist_ok=True)
    stimulus=ROOT/'simulations/integrated-recorder/stimulus/filtered-samples.csv'
    # Same recorded scaling fields; explicitly identify every substituted source.
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('acquisition_model',ROOT/'simulations/run_acquisition.py')
    model=module_from_spec(spec);spec.loader.exec_module(model)
    meta=model.metadata(2)
    meta.update(firmware='ad7606-2ch-1.6-driver-co-simulation',
        simulation_engine='native C: real drivers/serializer; ideal peripheral API model',
        hardware_variant='offline-co-simulation',imu_time='modeled_fifo_delta',
        notes='No RTOS scheduler, SDMMC or radio execution; modeled SPI/read times',
        modeled_duration_seconds=duration_seconds)
    metadata=result/'input-metadata.json';metadata.write_text(json.dumps(meta,separators=(',',':')))
    sources=[ROOT/'firmware/main'/name for name in
        ('adc_ad7606.c','sensors.c','sensors.h','imu_timing.h','format.c','format.h','board.h','variant.h')]
    with tempfile.TemporaryDirectory(prefix='afo-cosimulation-') as temp:
        binary=Path(temp)/'pipeline'
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-Wall','-Wextra','-Werror',
            '-I',str(P/'include'),'-I',str(ROOT/'firmware/main'),str(P/'pipeline.c'),
            *[str(s) for s in sources if s.suffix=='.c'],'-o',str(binary)],check=True)
        process=subprocess.run([str(binary),str(stimulus),str(metadata),str(result/'synthetic.afolog'),str(sample_count)],
            capture_output=True,text=True,check=True,timeout=60)
        (result/'execution.txt').write_text(process.stdout+process.stderr)
    export=Path(tempfile.mkdtemp(prefix='export-'))
    report=convert(result/'synthetic.afolog',export,make_plots=True)
    assert report['counts']['emg']==sample_count and report['no_detected_sample_loss'] and report['signal_checks_pass']
    assert report['emg_rate_from_host_timestamps_hz']==8000
    original=[(int(r['code1']),int(r['code2'])) for r in csv.DictReader(stimulus.open())]
    with (export/'emg.csv').open() as f:
        for i,row in enumerate(csv.DictReader(f)):
            assert (int(row['ch0_raw']),int(row['ch1_raw']))==original[i%8000]
        assert i+1==sample_count
    model_line=next(line[6:] for line in process.stdout.splitlines() if line.startswith('MODEL '))
    clock_accounting=json.loads(model_line)
    for sensor,identity in (('foot',1),('shank',2)):
        previous=None;rollovers=0;count=0
        with (export/f'{sensor}.csv').open() as f:
            for row in csv.DictReader(f):
                ticks=int(row['sensor_timestamp_raw']);estimate=int(row['host_time_estimate_us'])
                assert int(row['ax_raw'])==identity and int(row['ay_raw'])==0 and int(row['az_raw'])==2048
                assert all(int(row[name])==0 for name in ('gx_raw','gy_raw','gz_raw'))
                assert int(row['valid'])==1
                if previous is not None:
                    assert (ticks-previous[0])&65535==5000 and estimate-previous[1]==5000
                    rollovers+=ticks<previous[0]
                previous=(ticks,estimate);count+=1
        accounted=clock_accounting[sensor]
        assert count==report['counts'][sensor]==accounted['saved']
        assert count+accounted['pending_at_stop']==accounted['generated']
        assert rollovers==accounted['counter_rollovers']
        if duration_seconds>=60:assert rollovers>=900
    import shutil
    dest=result/'converted'
    if dest.exists():shutil.rmtree(dest)
    shutil.move(str(export),str(dest))
    summary={'pass':True,'hardware_measured':False,'esp32_executed':False,
        'production_sources_sha256':{s.name:hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
        'stimulus_sha256':hashlib.sha256(stimulus.read_bytes()).hexdigest(),
        'co_simulation_sha256':{s.name:hashlib.sha256(s.read_bytes()).hexdigest() for s in (P/'pipeline.c',P/'run.py',P/'include/mock_idf.h')},
        'modeled_duration_seconds':duration_seconds,'clock_accounting':clock_accounting,
        'imu_clock_drift_ppm':{'foot':70,'shank':-110},
        'imu_modeled_period_us':{'foot':5000*(1+70e-6),'shank':5000*(1-110e-6)},
        'stimulus_repeat_period_seconds':1,
        'boundary_note':'FIFO packets still buffered at the modeled stop are counted explicitly; no unseen packet is called a recorded measurement.',
        'groups_passed':sum(line.startswith('PASS ') for line in process.stdout.splitlines()),
        'quality':report,'limits':['Ideal peripheral API behavior; ordered native C execution',
            'Independent modeled IMU clocks; no calibrated physical alignment',
            'No RTOS scheduler, CPU contention, GPIO electrical levels, SDMMC or RF transport',
            'Ngspice input source and op-amp are approximations, not measured sensor/board behavior']}
    (result/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if compact_directory:
        compact=Path(compact_directory);compact.mkdir(parents=True,exist_ok=True)
        artifacts={}
        for file in (result/'synthetic.afolog', *(dest/name for name in ('emg.csv','foot.csv','shank.csv','status.csv'))):
            with file.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            artifacts[file.name]={'bytes':file.stat().st_size,'sha256':digest}
        (compact/'capture-artifacts.json').write_text(json.dumps({'artifacts':artifacts,
            'storage':'Full binary and CSV evidence retained in the local run output directory; package contains their hashes and summaries.'},indent=2)+'\n')
        for file in (result/'summary.json',result/'execution.txt',metadata,dest/'quality.json',dest/'signals.png'):
            shutil.copy2(file,compact/file.name)
    print(process.stdout,end='');print(f'PASS {sample_count} filtered-analog codes round-trip through C drivers, binary format and CSV')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=int,default=2,help='Modeled capture duration, 2 to 3600 seconds')
    parser.add_argument('--output',type=Path,help='Separate directory for full synthetic recording and CSV evidence')
    parser.add_argument('--compact-directory',type=Path,help='Copy compact summaries, artifact hashes and plot here')
    args=parser.parse_args()
    run(args.seconds,args.output,args.compact_directory)
