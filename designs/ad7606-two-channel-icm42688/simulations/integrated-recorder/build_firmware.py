#!/usr/bin/env python3
"""Build a simulation-only integrated recorder, never a hardware image."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

P=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-dir',type=Path,default=P/'build')
args=parser.parse_args()
build=args.build_dir.resolve()
subprocess.run(['idf.py','-C',str(P),'-B',str(build),'build'],check=True)
dest=P/'firmware';dest.mkdir(exist_ok=True)
shutil.copy2(build/'integrated_recorder.elf',dest/'integrated_recorder.elf')
shutil.copy2(P/'sdkconfig',dest/'effective-sdkconfig.txt')
subprocess.run([sys.executable,'-m','esptool','--chip','esp32s3','merge_bin',
    '-o',str(dest/'merged.bin'),'--flash_mode','dio','--flash_size','8MB','--flash_freq','80m',
    '0x0',str(build/'bootloader/bootloader.bin'),'0x8000',str(build/'partition_table/partition-table.bin'),
    '0x10000',str(build/'integrated_recorder.bin')],check=True)
root=P.parent.parent
sources=[root/'firmware/main'/n for n in ('main.c','adc_ad7606.c','sensors.c','sensors.h',
    'imu_timing.h','format.c','format.h','wifi_live.c','wifi_live.h','board.h','variant.h')]
sources += [P/'main/integration.c',P/'main/CMakeLists.txt',P/'CMakeLists.txt',P/'sdkconfig.defaults',
    P/'build_firmware.py',P/'wokwi.toml']
sources += sorted(f for f in (P/'chips').iterdir() if f.is_file())
manifest={'simulation_only':True,'hardware_measured':False,'idf_version':'v5.4.2',
    'substitutions':['Sparse PSRAM block disk in place of SDMMC','Fixture battery voltage and button/USB controls',
                     'UDP loopback subscriber instead of laptop radio link'],
    'trace_instrumentation':True,'task_watchdog_enabled':True,
    'sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources+
        list(dest.glob('*.bin'))+list(dest.glob('*.elf'))+[dest/'effective-sdkconfig.txt']}}
assert 'CONFIG_ESP_TASK_WDT_INIT=y' in (dest/'effective-sdkconfig.txt').read_text()
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Integrated simulation image prepared. Never flash this image onto the recorder.')
