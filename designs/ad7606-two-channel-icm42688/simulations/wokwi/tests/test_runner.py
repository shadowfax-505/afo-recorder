"""Evidence-gate tests with synthetic logs; these do not run ESP32 firmware."""
import importlib.util
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location('runner', Path(__file__).resolve().parents[1] / 'run_scenarios.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
NORMAL = '''ADC,elapsed_us=1000000,edges=8000,good=8000,ch1_mean=6554.00,min=6554,max=6554,rms_ac_codes=0.000,ch2_mean=13107.00,min=13107,max=13107,rms_ac_codes=0.000
IMU,0,packets=200,interrupts=200,ax_raw=1,ay_raw=0,az_raw=2048,gx_raw=0,gy_raw=0,gz_raw=0,timestamp_raw=16960
IMU,1,packets=200,interrupts=200,ax_raw=2,ay_raw=0,az_raw=2048,gx_raw=0,gy_raw=0,gz_raw=0,timestamp_raw=16960
WINDOW_COMPLETE; codes require comparison with applied test voltages
'''
VCD = '$timescale 1 ns $end\n$var wire 1 ! D0 $end\n$enddefinitions $end\n#0\n0!\n#125000\n1!\n'

class EvidenceTests(unittest.TestCase):
    def test_valid_normal(self):
        self.assertTrue(runner.assess('normal', NORMAL))

    def test_mean_cannot_hide_wrong_samples(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('min=6554,max=6554', 'min=6553,max=6555')))

    def test_reject_slow_acquisition(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('8000', '4000')))

    def test_reject_missing_conversion(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('good=8000', 'good=7999')))

    def test_reject_stale_imu_identity(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('ax_raw=2', 'ax_raw=1')))

    def test_reject_slow_imu(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('packets=200', 'packets=20')))

    def test_reject_partial_or_extra_window(self):
        self.assertFalse(runner.assess('normal', NORMAL.replace('WINDOW_COMPLETE;', '')))
        self.assertFalse(runner.assess('normal', NORMAL + NORMAL.splitlines()[0] + '\n'))

    def test_reject_later_failure(self):
        self.assertFalse(runner.assess('normal', NORMAL + 'FAIL,ADC late conversion/read,ESP_ERR_TIMEOUT\n'))

    def test_wrong_mode_requires_exact_model_signature(self):
        wrong = NORMAL.replace('6554', '-1').replace('13107', '-1')
        self.assertTrue(runner.assess('incorrect-mode', wrong))
        self.assertFalse(runner.assess('incorrect-mode', NORMAL.replace('6554', '5000')))

    def test_fault_must_be_a_diagnostic_line(self):
        self.assertTrue(runner.assess('stuck-busy', 'FAIL,ADC BUSY edge timeout,ESP_ERR_TIMEOUT\n'))
        self.assertFalse(runner.assess('stuck-busy', 'expected FAIL,ADC BUSY edge timeout\n'))
        self.assertFalse(runner.assess('stuck-busy', 'FAIL,ADC BUSY edge timeout,ESP_ERR_TIMEOUT\nFAIL,unrelated,ERR\n'))

    def test_interrupt_trace_checks_the_injected_foot_sensor(self):
        from verify_trace import verify
        header = '$timescale 1ns $end\n' + ''.join(
            f'$var wire 1 {chr(33+i)} D{i} $end\n' for i in range(8))
        trace = header + '$enddefinitions $end\n#0\n' + ''.join(
            f'{1 if i==2 else 0}{chr(33+i)}\n' for i in range(8))
        trace += '#100\n0#\n'
        for bit in range(128):
            trace += f'#{200+bit*200}\n1$\n#{300+bit*200}\n0$\n'
        trace += '#30000\n1#\n#5000000\n1\'\n#5000010\n0\'\n'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fault.vcd'
            p.write_text(trace)
            self.assertTrue(verify(p, 'missed-interrupt')['pass'])
            p.write_text(trace + '#6000000\n1&\n')
            self.assertFalse(verify(p, 'missed-interrupt')['pass'])

    def test_empty_or_header_only_trace_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'trace.vcd'
            self.assertFalse(runner.trace_has_activity(p))
            for data in ('', VCD.split('#125000')[0], VCD.replace('1!', '0!')):
                p.write_text(data)
                self.assertFalse(runner.trace_has_activity(p))
            p.write_text(VCD)
            self.assertTrue(runner.trace_has_activity(p))

    def test_stale_files_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'normal.serial.txt').write_text(NORMAL)
            (p / 'normal.vcd').write_text(VCD)
            result = runner.run_case('normal', p, lambda *a, **k: subprocess.CompletedProcess(a, 0, '', ''))
            self.assertFalse(result['pass'])
            self.assertFalse((p / 'normal.serial.txt').exists())
            self.assertFalse((p / 'normal.vcd').exists())

    def test_nonzero_exit_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            def execute(*args, **kwargs):
                (p / 'normal.serial.txt').write_text(NORMAL)
                (p / 'normal.vcd').write_text(VCD)
                return subprocess.CompletedProcess(args, 1, '', 'error')
            self.assertFalse(runner.run_case('normal', p, execute)['pass'])

    def test_timeout_and_missing_cli_report_failure(self):
        with tempfile.TemporaryDirectory() as d:
            for error in (subprocess.TimeoutExpired('wokwi', 120), FileNotFoundError('wokwi')):
                def execute(*a, **k):
                    raise error
                result = runner.run_case('normal', Path(d), execute)
                self.assertFalse(result['pass'])
                self.assertIn(type(error).__name__, result['error'])

if __name__ == '__main__':
    unittest.main()
