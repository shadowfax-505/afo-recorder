import io,unittest
from afo_format import EMG_B,make_header,read_header,make_record,decode_record,decode_emg_b,FormatError
class AD7606Tests(unittest.TestCase):
 def test_unplugged_bias_metadata_does_not_shift_raw_reconstruction(self):
  import csv,tempfile
  from pathlib import Path
  from convert import convert
  m=self.meta();m.update(unplugged_input_bias_mv=1500,unplugged_input_bias_ohm=1000000)
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'bias.afolog';out=Path(temp)/'csv'
   source.write_bytes(make_header(m)+make_record(7,1,125,EMG_B.pack(9830,6554,0,0,0,0,18,1,3,128)))
   convert(source,out,recover=True,make_plots=False)
   with (out/'emg.csv').open() as f:row=next(csv.DictReader(f))
   self.assertAlmostEqual(float(row['ch0_myoware_raw_v_estimate']),9830*5/32768)
   self.assertAlmostEqual(float(row['ch1_myoware_raw_v_estimate']),6554*5/32768)
   self.assertNotIn('ch2_raw',row)
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

 def test_live_ad7606_sample_gap_without_packet_loss(self):
  import json,tempfile
  from pathlib import Path
  from live_receiver import Capture
  from live_protocol import encode_packet
  with tempfile.TemporaryDirectory() as temp:
   cap=Capture(Path(temp)/'capture')
   try:
    cap.accept(encode_packet(1,10,1,1,json.dumps(self.meta()).encode()))
    records=b''.join(make_record(7,n,n*125,EMG_B.pack(9830,9830,0,0,0,0,18,1,3,n*125+3)) for n in (1,3))
    cap.accept(encode_packet(2,10,1,2,records,2))
    snap=cap.snapshot();self.assertEqual(snap['stats']['packet_gaps'],0);self.assertEqual(snap['sequence_gaps'][7],1);self.assertEqual(snap['first_sequence'][7],1)
   finally:cap.close()
