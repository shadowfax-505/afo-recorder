import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('timing_audit', P / 'audit_timing.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)


def imu_rows():
    return [dict(host_time_estimate_us=str(100000 + i * 5000), sensor_timestamp_raw=str((65530 + i * 5000) & 65535),
                 read_start_us=str(100100 + i * 5000), read_end_us=str(100400 + i * 5000),
                 irq_anchor_us=str(100000 + i * 5000), flags='2') for i in range(3)]


def emg_rows():
    return [dict(conversion_trigger_host_us=str(100000 + i * 125), read_start_us=str(100008 + i * 125),
                 read_duration_us='25', active_mask='3', sequence=str(i + 1), elapsed_slots='1', flags='0') for i in range(3)]


class TimingAuditTests(unittest.TestCase):
    def test_imu_rollover_rate(self):
        result = audit.imu_timing(imu_rows())
        self.assertTrue(result['pass']); self.assertEqual(result['sensor_counter_rate_hz'], 200)
        self.assertEqual(result['counter_rollovers'], 1)

    def test_estimate_reanchor_rejected(self):
        rows = imu_rows(); rows[1]['host_time_estimate_us'] = '104900'
        self.assertFalse(audit.imu_timing(rows)['pass'])

    def test_future_estimate_rejected(self):
        rows = imu_rows(); rows[0]['read_end_us'] = '99999'
        self.assertFalse(audit.imu_timing(rows)['pass'])

    def test_uncertainty_flag_required(self):
        rows = imu_rows(); rows[1]['flags'] = '0'
        self.assertFalse(audit.imu_timing(rows)['pass'])

    def test_emg_causality_and_read_margin(self):
        result = audit.emg_timing(emg_rows())
        self.assertTrue(result['pass']); self.assertEqual(result['read_end_to_next_trigger_us']['min'], 92)

    def test_read_crosses_next_trigger(self):
        rows = emg_rows(); rows[0]['read_duration_us'] = '130'
        self.assertFalse(audit.emg_timing(rows)['pass'])

    def test_sequence_gap_requires_flag(self):
        rows = emg_rows(); rows[1]['sequence'] = '3'; rows[1]['elapsed_slots'] = '2'; rows[2]['sequence'] = '4'
        self.assertFalse(audit.emg_timing(rows)['pass'])

    def test_known_nominal_capture(self):
        result = audit.audit_capture(P / 'results/current/normal')
        self.assertTrue(result['available_stream_timing_checks_pass'])
        self.assertEqual(result['streams']['foot']['sensor_counter_rate_hz'], 200)
        self.assertEqual(result['startup']['first_shank_minus_first_foot_estimate_us'], 55001)
        self.assertEqual(result['wifi_metadata_remaining_bytes'], 1)
        self.assertIsNone(result['full_case_execution_pass'])

    def test_existing_stuck_busy_trace(self):
        result = audit.audit_stuck_busy_trace(P / 'results/current/adc-stuck-busy/logic.vcd.gz')
        self.assertTrue(result['pass']); self.assertEqual(result['priming_reads'], 2)
        self.assertEqual(result['post_trigger_adc_reads'], 0)
        self.assertTrue(result['reset_not_observed'])


if __name__ == '__main__': unittest.main()
