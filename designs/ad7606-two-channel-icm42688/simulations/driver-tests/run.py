#!/usr/bin/env python3
"""Compile unmodified AD7606 C driver against a deterministic host peripheral shim."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

p = Path(__file__).resolve().parent
source = p.parents[1] / 'firmware/main/adc_ad7606.c'
sanitizers = ['address', 'undefined'] if os.environ.get('AFO_NATIVE_SANITIZERS') == '1' else []
compiler_flags = ['-std=c11', '-Wall', '-Wextra', '-Werror']
if sanitizers:
    compiler_flags += ['-fsanitize=' + ','.join(sanitizers), '-fno-omit-frame-pointer']
with tempfile.TemporaryDirectory(prefix='afo-driver-') as temp:
    binary = Path(temp) / 'test-driver'
    command = [os.environ.get('CC', 'cc'), *compiler_flags,
               '-I', str(p / 'include'), str(p / 'test_ad7606_driver.c'), '-o', str(binary)]
    subprocess.run(command, check=True)
    run = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
    print(run.stdout, end='')
    (p / 'results.txt').write_text(run.stdout)
    (p / 'results.json').write_text(json.dumps({
        'engine': 'native C compiler and mocked ESP-IDF peripheral APIs',
        'groups_passed': sum(line.startswith('PASS ') for line in run.stdout.splitlines()),
        'production_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'test_source_sha256': hashlib.sha256((p / 'test_ad7606_driver.c').read_bytes()).hexdigest(),
        'compiler_flags': compiler_flags, 'sanitizers': sanitizers,
        'esp32_executed': False, 'hardware_measured': False,
        'fixture': {'ordinary_busy_duration_us': 4, 'serial_transfer_duration_us': 16,
                    'independent_faults': ['disconnected/stuck-low BUSY', 'ignored CONVST',
                                          'stuck-high BUSY', 'late read', 'SPI API failure']},
        'limits': ['No scheduler, interrupt concurrency or GPIO electrical model',
                   'No ESP-IDF API implementation or actual SPI edge timing',
                   'Does not replace Wokwi system or physical tests']
    }, indent=2) + '\n')
    imu_binary=Path(temp)/'test-imu-timing'
    subprocess.run([os.environ.get('CC','cc'), *compiler_flags,
        str(p/'test_imu_timing.c'),'-o',str(imu_binary)],check=True)
    imu=subprocess.run([str(imu_binary)],capture_output=True,text=True,check=True)
    print(imu.stdout,end='');(p/'imu-timing-results.txt').write_text(imu.stdout)
    (p/'imu-timing-results.json').write_text(json.dumps({
        'engine':'native C compiler; production imu_timing.h',
        'groups_passed':sum(line.startswith('PASS ') for line in imu.stdout.splitlines()),
        'production_source_sha256':hashlib.sha256((source.parent/'imu_timing.h').read_bytes()).hexdigest(),
        'compiler_flags': compiler_flags, 'sanitizers': sanitizers,
        'hardware_measured':False,'esp32_executed':False,
        'limits':['Synthetic timestamp and read observations; no measured clock calibration or interrupt latency']
    },indent=2)+'\n')
