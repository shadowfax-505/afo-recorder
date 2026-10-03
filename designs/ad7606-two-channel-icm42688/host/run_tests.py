#!/usr/bin/env python3
"""Run the packaged reader, telemetry and fixed-two hardware contract tests."""
from pathlib import Path
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'host'))
sys.path.insert(1, str(ROOT / 'simulations'))


def main():
    if shutil.which('cc') is None:
        print('The full suite needs a C compiler named cc for the firmware channel-count guard. '
              'CSV conversion and the live receiver do not need a compiler.', file=sys.stderr)
        return 2
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'host/tests'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
