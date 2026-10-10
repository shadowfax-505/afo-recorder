import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from afo_format import (HEADER_SIZE, EMG, FIFO, FormatError, make_record,
                        decode_record, decode_fifo, read_header, iter_records)
from convert import convert
from generate_example import generate

class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'trial.afolog';generate(self.source,.2)
    def tearDown(self):self.temp.cleanup()
    def run_export(self,**kwargs):
        return convert(self.source,self.root/'export',make_plots=False,**kwargs)
    def test_clean_recording(self):
        report=self.run_export()
        self.assertTrue(report['no_detected_sample_loss']);self.assertTrue(report['signal_checks_pass'])
        self.assertEqual(report['counts']['emg'],1600);self.assertEqual(report['counts']['foot'],40)
        self.assertAlmostEqual(report['emg_rate_from_host_timestamps_hz'],8000)
        self.assertFalse(report['research_ready'])
    def test_crc_reference(self):
        self.assertEqual(zlib.crc32(b'123456789'),0xcbf43926)
        r=make_record(1,1,500,EMG.pack(0,4095,24,26,24,1))
        self.assertEqual(len(r),64);self.assertEqual(decode_record(r).timestamp_us,500)
    def test_corrupt_header_is_not_recoverable(self):
        data=bytearray(self.source.read_bytes());data[100]^=1;self.source.write_bytes(data)
        with self.assertRaises(FormatError):self.run_export(recover=True)
    def test_unknown_version(self):
        data=bytearray(self.source.read_bytes());struct.pack_into('<H',data,8,2)
        struct.pack_into('<I',data,4092,zlib.crc32(data[:4092]));self.source.write_bytes(data)
        with self.assertRaises(FormatError):self.run_export()
    def test_crc_corruption_strict(self):
        data=bytearray(self.source.read_bytes());data[HEADER_SIZE+30]^=1;self.source.write_bytes(data)
        with self.assertRaises(FormatError):self.run_export()
        self.assertTrue((self.root/'export'/'CONVERSION_FAILED.txt').exists())
    def test_crc_corruption_recovery(self):
        data=bytearray(self.source.read_bytes());data[HEADER_SIZE+30]^=1;self.source.write_bytes(data)
        report=self.run_export(recover=True)
        self.assertFalse(report['no_detected_sample_loss']);self.assertEqual(report['counts']['emg'],1599)
        self.assertEqual(report['sequence_gaps']['emg'],1)
    def test_byte_insertion_resynchronizes(self):
        data=self.source.read_bytes();self.source.write_bytes(data[:4096]+b'BAD'+data[4096:])
        report=self.run_export(recover=True)
        self.assertEqual(report['counts']['emg'],1600);self.assertFalse(report['structurally_complete'])
    def test_truncated_tail_recovery(self):
        self.source.write_bytes(self.source.read_bytes()[:-13])
        report=self.run_export(recover=True)
        self.assertFalse(report['session_finalized']);self.assertFalse(report['no_detected_sample_loss'])
    def test_missing_end_on_record_boundary(self):
        self.source.write_bytes(self.source.read_bytes()[:-64])
        self.assertFalse(self.run_export()['session_finalized'])
    def test_timer_gap_is_visible(self):
        self.source.unlink();generate(self.source,.2,skip_slot=42)
        report=self.run_export()
        self.assertEqual(report['emg_observed_skipped_slots'],1)
        self.assertEqual(report['sequence_gaps']['emg'],1)
        self.assertFalse(report['no_detected_sample_loss'])
    def test_fifo_signed_values_and_timestamp(self):
        p=decode_fifo(FIFO.pack(0x68,-123,456,2048,-200,50,0,-3,65530))
        self.assertEqual(p['ax'],-123);self.assertEqual(p['temperature_raw'],-3)
        self.assertEqual(p['sensor_timestamp_raw'],65530)
    def test_fifo_invalid_marker(self):
        self.assertFalse(decode_fifo(FIFO.pack(0x68,-32768,0,0,0,0,0,0,3))['valid'])
    def test_timestamp_wrap(self):
        report=self.run_export();self.assertEqual(report['anomalies']['imu_timestamp_anomalies'],0)
        import csv
        with (self.root/'export'/'foot.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertEqual(int(rows[-1]['sensor_time_unwrapped_us']),200000)
    def test_imu_clock_screen_nominal(self):
        source=self.root/'long.afolog';generate(source,11)
        clock=convert(source,self.root/'long',make_plots=False)['imu_clock']
        for name in ('foot','shank'):
            self.assertEqual(clock[name]['median_tick_step'],5000)
            self.assertAlmostEqual(clock[name]['host_us_per_sensor_tick'],1.0,places=6)
            self.assertTrue(clock[name]['within_1_percent'])
    def test_imu_clock_screen_reports_wrong_tick_scale(self):
        # Sensor ticks 6.7% longer than 1 us: still inside the +/-20% anomaly
        # window, so only the clock screen reveals it.
        source=self.root/'scaled.afolog';generate(source,11,imu_tick_step=4688)
        report=convert(source,self.root/'scaled',make_plots=False)
        self.assertEqual(report['anomalies']['imu_timestamp_anomalies'],0)
        clock=report['imu_clock']['foot']
        self.assertEqual(clock['median_tick_step'],4688)
        self.assertAlmostEqual(clock['host_us_per_sensor_tick'],5000/4688,places=4)
        self.assertFalse(clock['within_1_percent'])
    def test_imu_clock_screen_needs_span(self):
        clock=self.run_export()['imu_clock']['foot']
        self.assertIsNone(clock['host_us_per_sensor_tick']);self.assertIsNotNone(clock['fit_note'])
    def test_no_overwrite(self):
        self.run_export()
        with self.assertRaises(ValueError):self.run_export()
    def test_data_after_end_rejected(self):
        with self.source.open('ab') as f:f.write(make_record(1,1601,1200200,EMG.pack(1,2,25,27,25,1)))
        with self.assertRaises(FormatError):self.run_export()
    def test_voltage_conversion_uses_adc_bin_width(self):
        import csv
        self.run_export()
        with (self.root/'export'/'emg.csv').open() as f:r=next(csv.DictReader(f))
        self.assertAlmostEqual(float(r['ch0_voltage']),int(r['ch0_raw'])*3.3/4096)
        self.assertEqual(int(r['ch1_transaction_start_us'])-int(r['ch0_transaction_start_us']),27)
    def test_future_record_type_rejected(self):
        data=bytearray(make_record(1,1,500,EMG.pack(1,2,24,26,24,1)));data[4]=99
        struct.pack_into('<I',data,60,zlib.crc32(data[:60]))
        with self.assertRaises(FormatError):decode_record(data)
    def test_empty_file_rejected(self):
        with self.assertRaises(FormatError):read_header(io.BytesIO())
    def test_emg_only_bench_mode(self):
        self.source.unlink();generate(self.source,.2,imu_enabled=False)
        report=self.run_export()
        self.assertEqual(report['counts']['foot'],0)
        self.assertTrue(report['no_detected_sample_loss'])

if __name__=='__main__':unittest.main()
