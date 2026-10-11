#!/usr/bin/env python3
"""Compile and run the production ICM-42688 driver against the register-level model."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;VARIANT=HERE.parents[1];MAIN=VARIANT/'firmware/main'
def main():
    with tempfile.TemporaryDirectory(prefix='icm-model-') as temp:
        binary=Path(temp)/'icm_model_test'
        command=[os.environ.get('CC','cc'),'-std=gnu11','-O1','-Wall','-Wextra','-Werror','-I',str(HERE),
                 '-I',str(VARIANT/'simulations/offline-pipeline/include'),'-I',str(MAIN),'-DAFO_AD7606=1']
        if os.environ.get('AFO_NATIVE_SANITIZERS')=='1':command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(command+[str(HERE/'test_icm_model.c'),str(HERE/'icm42688_model.c'),str(MAIN/'sensors.c'),'-lm','-o',str(binary)],check=True)
        run=subprocess.run([str(binary)],capture_output=True,text=True)
    (HERE/'results.txt').write_text(run.stdout)
    lines=run.stdout.splitlines()
    report={'engine':'native C; production sensors.c and imu_timing.h; register-level ICM-42688-P model from DS-000347 rules',
            'checks_passed':sum(l.startswith('PASS ') for l in lines),'checks_failed':sum(l.startswith('FAIL ') for l in lines),
            'pass':run.returncode==0,'sanitizers':os.environ.get('AFO_NATIVE_SANITIZERS')=='1',
            'production_sources_sha256':{n:hashlib.sha256((MAIN/n).read_bytes()).hexdigest() for n in ('sensors.c','imu_timing.h','board.h')},
            'model_sources_sha256':{n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('icm42688_model.c','icm42688_model.h','test_icm_model.c')},
            'hardware_measured':False,
            'limits':['Behavioral register model written from the datasheet; it cannot reveal silicon errata, counterfeit parts, wrong jumpers or wiring faults beyond the modeled cases',
                      'No analog sensor physics: noise, bias, scale error, temperature and vibration are not modeled',
                      'SPI is transaction-level; signal integrity on a breadboard is not modeled',
                      'The 32/30 us tick follows DS-000347 section 12.7 and is confirmed by the stage-6 bench check'],
            'stdout':lines}
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(run.stdout,end='');return run.returncode
if __name__=='__main__':raise SystemExit(main())
