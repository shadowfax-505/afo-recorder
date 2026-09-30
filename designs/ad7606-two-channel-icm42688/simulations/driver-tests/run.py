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
with tempfile.TemporaryDirectory(prefix='afo-driver-') as temp:
    binary = Path(temp) / 'test-driver'
    command = [os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
               '-I', str(p / 'include'), str(p / 'test_ad7606_driver.c'), '-o', str(binary)]
    subprocess.run(command, check=True)
    run = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
    print(run.stdout, end='')
    (p / 'results.txt').write_text(run.stdout)
    (p / 'results.json').write_text(json.dumps({
        'engine': 'native C compiler and mocked ESP-IDF peripheral APIs',
        'groups_passed': sum(line.startswith('PASS ') for line in run.stdout.splitlines()),
        'production_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'esp32_executed': False, 'hardware_measured': False,
        'limits': ['No scheduler, interrupt concurrency or GPIO electrical model',
                   'No ESP-IDF API implementation or actual SPI edge timing',
                   'Does not replace Wokwi system or physical tests']
    }, indent=2) + '\n')
