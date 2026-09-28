import csv,io,json,struct,tempfile,unittest
from pathlib import Path
from afo_format import *
from convert import convert
from live_receiver import Capture
from live_protocol import encode_packet
class MPUTests(unittest.TestCase):
 def meta(self):
  return dict(schema='afo-recorder/3',adc_model='AD7606',adc_bits=16,adc_reference_mv=5000,input_scale=1,input_midpoint_mv=0,adc_osr=1,adc_sensor_crc_supported=False,emg_hz=8000,imu_hz=200,active_channel_count=2,emg_channels=['EMG1','EMG2'],record_bytes=64,calibration_state='uncalibrated',adc_pga=1,accel_range_g=16,gyro_range_dps=2000,imu_model='MPU6050',imu_packet_format='mpu6050-fifo12-batch-v1',imu_timestamp_tick_us=None,accel_lsb_per_g=2048,gyro_lsb_per_dps=16.4,synthetic=True)
 def packet(self,index=0,count=1):return struct.pack('>6h',-2048,0,2048,-164,328,-492)+struct.pack('<HH',index,count)
 def record(self,kind=8,n=1,flags=2):return make_record(kind,n,n*5000,IMU.pack(self.packet(),n*5000+10,n*5000+100,n*5000),flags)
 def test_axes_and_signed_decode(self):
  d=decode_mpu(self.packet(),self.meta());self.assertEqual([d[k] for k in ('ax','ay','az','gx','gy','gz')],[-2048,0,2048,-164,328,-492]);self.assertIsNone(d['sensor_timestamp_raw'])
 def test_batch_validation(self):
  for i,n in [(1,1),(0,0),(0,86)]:
   with self.assertRaises(FormatError):decode_mpu(self.packet(i,n),self.meta())
 def test_metadata_mismatch(self):
  m=self.meta();m['imu_model']='ICM42688'
  with self.assertRaises(FormatError):decode_mpu(self.packet(),m)
 def trial(self,path,flags=2,overflow=0):
  data=make_header(self.meta())+make_record(7,1,125,EMG_B.pack(0,0,0,0,0,0,10,1,3,125))+self.record(8,1,flags)+self.record(9,1,flags)
  data+=make_record(5,1,10000,STATUS.pack(0,0,0,overflow,0,1,1,1,3800,3),0 if not overflow else 3)
  path.write_bytes(data)
 def test_conversion_no_invented_clock_and_scaling(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);self.trial(p/'trial.afolog');r=convert(p/'trial.afolog',p/'out',make_plots=False)
   self.assertTrue(r['no_detected_sample_loss']);self.assertEqual(r['anomalies']['timing_uncertain_records'],2)
   row=next(csv.DictReader((p/'out/foot.csv').open()));self.assertEqual(row['sensor_timestamp_raw'],'');self.assertEqual(float(row['gx_dps']),-10);self.assertEqual(row['fifo_batch_count'],'1')
 def test_irq_gap_visible(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);self.trial(p/'x',3);r=convert(p/'x',p/'out',make_plots=False);self.assertFalse(r['signal_checks_pass']);self.assertEqual(r['anomalies']['flagged_gap_records'],2)
 def test_fifo_overflow_visible(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);self.trial(p/'x',overflow=1);r=convert(p/'x',p/'out',make_plots=False);self.assertFalse(r['no_detected_sample_loss'])
 def test_live_two_identities_and_missing_samples(self):
  with tempfile.TemporaryDirectory() as t:
   c=Capture(Path(t)/'capture')
   try:
    c.accept(encode_packet(1,10,1,1,json.dumps(self.meta()).encode()))
    c.accept(encode_packet(2,10,1,2,self.record(8,1)+self.record(9,1)+self.record(8,3),3))
    s=c.snapshot();self.assertEqual(s['sequence_gaps'][8],1);self.assertEqual(set(s['imu']),{'foot','shank'});self.assertAlmostEqual(s['imu']['foot']['gyro_dps'][0],-10)
   finally:c.close()
 def test_truncation_recovery(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);self.trial(p/'x');(p/'x').write_bytes((p/'x').read_bytes()[:-9]);r=convert(p/'x',p/'out',recover=True,make_plots=False);self.assertFalse(r['session_finalized'])
