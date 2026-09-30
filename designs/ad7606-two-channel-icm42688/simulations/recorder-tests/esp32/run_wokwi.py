#!/usr/bin/env python3
"""Require fresh complete serial evidence for the actual ESP-IDF task test."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
VARIANT = HERE.parents[2]
if not os.environ.get('WOKWI_CLI_TOKEN'):
    raise SystemExit('Set WOKWI_CLI_TOKEN locally before running; never commit the credential.')
out = HERE / 'results'
out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='afo-lifecycle-wokwi-') as name:
    serial = Path(name) / 'serial.txt'
    command = [os.environ.get('WOKWI_CLI', 'wokwi-cli'), str(HERE), '--timeout', '6000',
               '--expect-text', 'LIFECYCLE_COMPLETE,cases=300,hardware_measured=false',
               '--fail-text', 'assert failed', '--serial-log-file', str(serial)]
    process = subprocess.run(command, capture_output=True, text=True, timeout=180)
    content = serial.read_text() if serial.exists() else ''
    families = re.findall(r'^LIFECYCLE_PASS,family=(\d+),cycles=100$', content, re.M)
    complete = 'LIFECYCLE_COMPLETE,cases=300,hardware_measured=false' in content
    passed = process.returncode == 0 and families == ['0', '1', '2'] and complete
    passed = passed and not any(text in content for text in ('assert failed', 'Guru Meditation', 'abort()'))
    (out / 'serial.txt').write_text(content)
    (out / 'cli.txt').write_text(process.stdout + process.stderr)
    report = {
        'engine': 'Wokwi CLI; actual ESP-IDF v5.4.2 ESP32-S3 FreeRTOS execution',
        'pass': passed, 'families': {'0': 'normal join', '1': 'faulted workers suspended before join',
                                     '2': 'join with EMG worker only; absent IMU task completion bit'},
        'cycles_per_family': 100, 'cases_passed': 300 if passed else 0,
        'exit_code': process.returncode, 'esp32_executed': True, 'hardware_measured': False,
        'production_main_sha256': hashlib.sha256((VARIANT / 'firmware/main/main.c').read_bytes()).hexdigest(),
        'harness_sha256': hashlib.sha256((HERE / 'main/lifecycle.c').read_bytes()).hexdigest(),
        'firmware_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (HERE / 'firmware').iterdir() if p.is_file()},
        'limits': ['Peripheral entry points are stubs; no ADC/IMU input or SD/radio execution',
                   'Real FreeRTOS tasks and production join/retire/fault functions are exercised',
                   'No physical core, timing, rail, flash persistence or endurance measurements'],
    }
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    if not passed:
        raise SystemExit('Lifecycle simulation failed; inspect fresh results/serial.txt and cli.txt.')
    print('PASS: 300 task lifecycle cycles on simulated ESP32-S3 FreeRTOS.')
