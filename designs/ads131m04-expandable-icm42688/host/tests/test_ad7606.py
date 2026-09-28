import io,unittest
from afo_format import EMG_B,make_header,read_header,make_record,decode_record,decode_emg_b,FormatError
class AD7606Tests(unittest.TestCase):
 def meta(self,count=2):
  return dict(schema='afo-recorder/3',adc_model='AD7606',adc_bits=16,adc_reference_mv=5000,input_scale=1,input_midpoint_mv=0,adc_osr=1,adc_sensor_crc_supported=False,emg_hz=8000,imu_hz=200,active_channel_count=count,emg_channels=['EMG'+str(i+1) for i in range(count)],record_bytes=64,calibration_state='uncalibrated',adc_pga=1,accel_range_g=16,gyro_range_dps=2000,imu_timestamp_tick_us=1)
 def rec(self,values,mask=3,status=0,crc=0):return decode_record(make_record(7,1,125,EMG_B.pack(*values,status,crc,18,1,mask,128)))
 def test_signed_limits_and_disabled(self):
  m=read_header(io.BytesIO(make_header(self.meta())))
  values,*_=decode_emg_b(self.rec([-32768,32767,0,0]),m);self.assertEqual(tuple(values),(-32768,32767))
  for values in [[-32769,0,0,0],[32768,0,0,0],[0,0,1,0]]:
   with self.assertRaises(FormatError):decode_emg_b(self.rec(values),m)
  with self.assertRaises(FormatError):decode_emg_b(self.rec([0,0,0,0],15),m)
 def test_no_chip_crc_claim(self):
  m=self.meta()
  for status,crc in [(1,0),(0,1)]:
   with self.assertRaises(FormatError):decode_emg_b(self.rec([0,0,0,0],status=status,crc=crc),m)
  m['adc_sensor_crc_supported']=True
  with self.assertRaises(FormatError):read_header(io.BytesIO(make_header(m)))
