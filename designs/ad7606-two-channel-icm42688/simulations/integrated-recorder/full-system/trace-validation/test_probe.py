"""Fault injection checks for the pin observer and its independent decoder.

All native fixture edges are synthetic. They test the measuring instrument,
not ESP32 execution; the separate browser capture supplies recorder evidence.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from assess_probe import entries, qualify

P = Path(__file__).resolve().parent


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='afo-probe-tests-')
        cls.binary = Path(cls.temp.name) / 'probe-fixture'
        compiler = shutil.which('cc')
        if not compiler:
            raise unittest.SkipTest('Native C compiler unavailable')
        subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                        str(P / 'probe_fixture.c'), '-o', str(cls.binary)], check=True)
        cls.nominal = cls.capture('normal')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def capture(cls, case):
        return subprocess.run([str(cls.binary), case], check=True, capture_output=True, text=True).stdout

    def test_nominal(self):
        result = qualify(self.nominal, 128)
        self.assertTrue(result['pass'], result['errors'])
        self.assertEqual(result['raw_edge_check']['complete_frames'], 2)
        self.assertEqual(result['observer']['priming_reads'], 2)

    def test_same_time_busy_before_trigger(self):
        self.assertTrue(qualify(self.capture('busy-first'), 128)['pass'])

    def test_hardware_and_full_trace_labels(self):
        result = qualify(self.nominal, 128)
        self.assertFalse(result['hardware_measured'])
        self.assertFalse(result['research_ready'])
        self.assertFalse(result['full_session_vcd_qualified'])
        self.assertFalse(result['clock_idle_polarity_qualified'])

    def test_injected_protocol_and_timing_faults(self):
        for case in ['short-clock', 'swapped-words', 'missing-busy', 'read-busy',
                     'wrong-idle', 'prime-reset', 'slow-clock', 'slow-trigger',
                     'missing-foot-irq', 'partial-frame', 'late-trigger', 'missing-prime']:
            with self.subTest(case=case):
                result = qualify(self.capture(case), 128)
                self.assertFalse(result['pass'], case)

    def test_saved_counter_mismatch(self):
        self.assertFalse(qualify(self.nominal, 127)['pass'])

    def test_duplicate_summary(self):
        with self.assertRaises(ValueError):
            qualify(self.nominal + self.nominal, 128)

    def test_truncated_summary(self):
        with self.assertRaises(ValueError):
            qualify(self.nominal[:self.nominal.index('PROBE_SUMMARY')], 128)

    def test_deleted_edges_cannot_hide_behind_good_summary(self):
        # Keep the observer's good summary, remove the actual clock evidence.
        text = '\n'.join(line for line in self.nominal.splitlines() if ',SCLK,' not in line)
        self.assertFalse(qualify(text, 128)['pass'])

    def test_bad_data_edges_cannot_hide_behind_good_summary(self):
        # Replace every observed data bit; the independent decoder must reject it.
        text = '\n'.join(line.rsplit(',', 1)[0] + ',0' if ',DOUTA,' in line else line
                         for line in self.nominal.splitlines())
        self.assertFalse(qualify(text, 128)['pass'])

    def test_split_visible_console_rows(self):
        line = next(line for line in self.nominal.splitlines() if line.startswith('PROBE_SUMMARY,'))
        split = 1000
        text = self.nominal.replace(line, 'chip-probe\n\u00a0' + line[:split] + '\nchip-probe\n\u00a0' + line[split:])
        self.assertEqual(entries(text, 'PROBE_SUMMARY'), entries(self.nominal, 'PROBE_SUMMARY'))
        self.assertTrue(qualify(text, 128)['pass'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProbeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'pass': result.wasSuccessful(), 'tests': result.testsRun, 'fault_variations': 12,
              'hardware_measured': False, 'fixture_edges': 'synthetic native instrument tests',
              'failed': [test.id() for test, _ in result.failures + result.errors]}
    (P / 'instrument-tests.json').write_text(json.dumps(report, indent=2) + '\n')
    raise SystemExit(not result.wasSuccessful())
