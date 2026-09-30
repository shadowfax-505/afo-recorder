#!/usr/bin/env python3
"""Build the simulation-only lifecycle image from an activated ESP-IDF shell."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-dir', type=Path, default=here / 'build')
args = parser.parse_args()
build = args.build_dir.resolve()
subprocess.run(['idf.py', '-C', str(here), '-B', str(build), 'build'], check=True)
destination = here / 'firmware'
destination.mkdir(exist_ok=True)
shutil.copy2(build / 'recorder_lifecycle.elf', destination / 'recorder_lifecycle.elf')
subprocess.run([sys.executable, '-m', 'esptool', '--chip', 'esp32s3', 'merge_bin',
                '-o', str(destination / 'merged.bin'), '--flash_mode', 'dio',
                '--flash_size', '8MB', '--flash_freq', '80m',
                '0x0', str(build / 'bootloader/bootloader.bin'),
                '0x8000', str(build / 'partition_table/partition-table.bin'),
                '0x10000', str(build / 'recorder_lifecycle.bin')], check=True)
print('Simulation image prepared. This image cannot record from hardware.')
