#!/usr/bin/env python3
"""Build the isolated QEMU fixture; never flash its image onto hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir',type=Path,required=True)
    args=parser.parse_args();build=args.build_dir.resolve()
    original=HERE.parent/'integrated-recorder/main/integration.c'
    source=original.read_text()
    assert source.count('void app_main(void)')==1
    adapted=source.replace('void app_main(void)','void qemu_fixture_main(void)').replace('__real_gpio_get_level','qemu_model_gpio_get_level')
    (HERE/'main/fixture.c').write_text('// Adapted simulation fixture; production firmware sources are included unchanged.\n#include "model.h"\n'+adapted)
    idf=shutil.which('idf.py')
    if not idf or not os.environ.get('IDF_PATH'):raise SystemExit('Activate ESP-IDF v5.4.2 before building.')
    subprocess.run([idf,'-C',str(HERE),'-B',str(build),'build'],check=True)
    subprocess.run([sys.executable,'-m','esptool','--chip','esp32s3','merge_bin','--fill-flash-size','8MB',
        '-o','qemu-flash.bin','@flash_args'],cwd=build,check=True)
    output=HERE/'firmware';output.mkdir(exist_ok=True)
    for name in ('qemu_recorder.elf','qemu-flash.bin'):shutil.copy2(build/name,output/name)
    shutil.copy2(HERE/'sdkconfig',output/'effective-sdkconfig.txt')
    files=[path for path in (ROOT/'firmware/main').iterdir() if path.suffix in ('.c','.h')]
    files+=list((HERE/'main').glob('*'))+[HERE/'sdkconfig.defaults',HERE/'CMakeLists.txt',
        original,HERE.parent/'integrated-recorder/chips/stimulus.h',
        output/'qemu_recorder.elf',output/'qemu-flash.bin',output/'effective-sdkconfig.txt']
    manifest={'firmware_version':'ad7606-2ch-1.6','engine':'Espressif QEMU ESP32-S3',
        'simulation_only':True,'hardware_measured':False,'physical_acceptance_pass':False,
        'sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in files if path.is_file()}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built simulation-only QEMU image and source/image manifest.')

if __name__=='__main__':main()
