#!/usr/bin/env python3
"""Compile the current behavioral AD7606 chip C against independent native API stubs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

P = Path(__file__).resolve().parent
SIM = P.parent
sanitizers = ['address', 'undefined'] if os.environ.get('AFO_NATIVE_SANITIZERS') == '1' else []
flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unknown-attributes', '-Wno-unused-function']
if sanitizers: flags += ['-fsanitize=' + ','.join(sanitizers), '-fno-omit-frame-pointer']
with tempfile.TemporaryDirectory(prefix='afo-chip-model-') as directory:
    binary = Path(directory) / 'model-test'
    subprocess.run([os.environ.get('CC', 'cc'), *flags, str(P / 'test_ad7606_model.c'), '-o', str(binary)], check=True)
    run = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
    print(run.stdout, end='')
    (SIM / 'model-test-results.txt').write_text(run.stdout)
    result = {'engine': 'native C compiler; current behavioral AD7606 chip with independent API stubs',
              'groups_passed': sum(line.startswith('PASS ') for line in run.stdout.splitlines()),
              'hardware_measured': False, 'esp32_executed': False, 'wasm_executed': False,
              'compiler_flags': flags, 'sanitizers': sanitizers,
              'sha256': {str(path.relative_to(SIM)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [SIM / 'chips/ad7606.chip.c', SIM / 'chips/stimulus.h', SIM / 'chips/wokwi-api.h',
                                      P / 'test_ad7606_model.c', P / 'run_model_tests.py']},
              'limits': ['Manual pin changes and timer completion invoke the actual C callbacks without the Wokwi runtime.',
                         'Checks behavioral-model consistency, not manufacturer silicon, voltage levels or analog timing.',
                         'No actual firmware acquisition, RTOS scheduler, SPI wire edges or complete system execution.']}
    (SIM / 'model-test-results.json').write_text(json.dumps(result, indent=2) + '\n')
