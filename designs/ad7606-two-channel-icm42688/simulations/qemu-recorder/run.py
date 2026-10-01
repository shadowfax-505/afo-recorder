#!/usr/bin/env python3
"""Run a bounded offline ESP32-S3 integration experiment; not a hardware test."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import tempfile
import threading
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('integrated_assessment',HERE.parent/'integrated-recorder/run.py')
assessment=importlib.util.module_from_spec(spec)
spec.loader.exec_module(assessment)

def execute(case,out,qemu,image,wall_timeout=60,icount=None):
    out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((HERE/'firmware/manifest.json').read_text())
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((HERE.parent.parent/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Source or image changed since compilation: '+name)
    if hashlib.sha256(image.read_bytes()).hexdigest()!=manifest['sha256']['simulations/qemu-recorder/firmware/qemu-flash.bin']:
        raise ValueError('The supplied image does not match the compiled fixture manifest')
    (out/'tested-build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    number,_=assessment.CASES[case]
    adc=4 if case=='adc-busy-stays-low' else 5 if case=='adc-trigger-ignored' else 1 if number==6 else 0
    imu=2 if number==7 else 3 if number==8 else 1 if number==15 else 0
    monitor_dir=tempfile.TemporaryDirectory(prefix='afo-qemu-',dir='/tmp')
    monitor_path=str(Path(monitor_dir.name)/'monitor.sock')
    temporary_flash=Path(monitor_dir.name)/'flash.bin'
    shutil.copy2(image,temporary_flash)
    command=[str(qemu),'-machine','esp32s3','-nographic','-monitor','none','-serial','stdio',
             '-m','8M','-global','driver=ssi_psram,property=is_octal,value=true',
             '-drive',f'file={temporary_flash},if=mtd,format=raw','-no-reboot',
             '-qmp',f'unix:{monitor_path},server=on,wait=off']
    if icount is not None:command+=['-icount',f'shift={icount},align=off,sleep=off']
    (out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    (out/'input-image.json').write_text(json.dumps({'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
        'fresh_copy_per_case':True},indent=2)+'\n')
    lines=queue.Queue()
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def reader():
        with (out/'serial.txt').open('wb') as log:
            for line in iter(process.stdout.readline,b''):
                log.write(line);log.flush();lines.put(line)
        lines.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    completed=False;configured=False;deadline=time.monotonic()+wall_timeout
    try:
        while time.monotonic()<deadline:
            try:line=lines.get(timeout=1)
            except queue.Empty:continue
            if line is None:break
            if b'QEMU_CONFIG_REQUEST' in line:
                process.stdin.write(f'{number} {adc} {imu}\n'.encode());process.stdin.flush();configured=True
            if line.startswith(b'INTEGRATED_RESULT') or b'assert failed:' in line or b'Guru Meditation' in line:
                print(line.decode(errors='replace').strip(),flush=True)
            if line.startswith(f'INTEGRATED_COMPLETE,case={number},'.encode()):completed=True;break
    finally:
        if not completed:
            try:
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as monitor:
                    monitor.settimeout(2);monitor.connect(monitor_path)
                    stream=monitor.makefile('rwb',buffering=0)
                    replies=[json.loads(stream.readline())]
                    for request in ({'execute':'qmp_capabilities'},
                        {'execute':'human-monitor-command','arguments':{'command-line':'info registers -a'}}):
                        stream.write(json.dumps(request).encode()+b'\n')
                        replies.append(json.loads(stream.readline()))
                    (out/'emulator-state.json').write_text(json.dumps(replies,indent=2)+'\n')
            except (OSError,ValueError):pass
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        thread.join(timeout=5)
        monitor_dir.cleanup()
    result={'case':case,'engine':'Espressif QEMU ESP32-S3','configured':configured,
            'completed':completed,'pass':False,'hardware_measured':False,'physical_acceptance_pass':False,
            'clock_mode':'wall_paced' if icount is None else 'instruction_count_shift_'+icount}
    try:
        if not completed:raise ValueError('No complete execution/export within wall-clock limit')
        result.update(assessment.assess(case,(out/'serial.txt').read_text(errors='replace'),out))
        # The shared assessment creates a synthetic tag. Identify this engine accurately.
        recording=out/'simulated-recording.afolog'
        if recording.exists():
            import io
            raw=recording.read_bytes();meta=assessment.read_header(io.BytesIO(raw));meta['simulation']='QEMU integrated recorder with SDK peripheral substitutes'
            recording.write_bytes(assessment.make_header(meta)+raw[assessment.HEADER_SIZE:])
            (out/'converted').rename(out/'assessment-conversion')
            result['quality']=assessment.convert(recording,out/'converted',make_plots=(number==14))
            shutil.rmtree(out/'assessment-conversion')
    except (ValueError,KeyError,OSError) as error:result.update(error=str(error),pass_=False);result['pass']=False;result.pop('pass_',None)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result.get(k) for k in ('case','pass','completed','error','failures')}),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu',type=Path,required=True)
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--case',choices=list(assessment.CASES),action='append')
    parser.add_argument('--icount',choices=['auto','0','1','2','3','4'])
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    results=[execute(case,args.out/case,args.qemu.resolve(),args.image.resolve(),icount=args.icount) for case in args.case or assessment.CASES]
    summary={'engine':'Espressif QEMU ESP32-S3 with documented peripheral substitutes','hardware_measured':False,
             'physical_acceptance_pass':False,'cases_passed':sum(x['pass'] for x in results),'cases':results}
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if all(x['pass'] for x in results) else 1

if __name__=='__main__':raise SystemExit(main())
