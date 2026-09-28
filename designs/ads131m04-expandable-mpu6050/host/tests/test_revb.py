import unittest,io,tempfile,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'simulations'))
from run_acquisition import metadata,frame,generate
from afo_format import *
from convert import convert
from live_receiver import Capture
from live_protocol import encode_packet
class RevisionBTests(unittest.TestCase):
 def test_modes_and_disabled_channels(self):
  for count in (2,4):
   m=read_header(io.BytesIO(make_header(metadata(count))))
   r=decode_record(frame(1,125,count));codes,*_=decode_emg_b(r,m);self.assertEqual(len(codes),count)
   bad=list(EMG_B.unpack(r.payload));bad[8]=15 if count==2 else 3
   with self.assertRaises(FormatError):decode_emg_b(decode_record(make_record(r.kind,1,125,EMG_B.pack(*bad))),m)
  m=metadata(2);r=decode_record(frame(1,125,2));bad=list(EMG_B.unpack(r.payload));bad[2]=1
  with self.assertRaises(FormatError):decode_emg_b(decode_record(make_record(r.kind,1,125,EMG_B.pack(*bad))),m)
 def test_metadata_rejects_unsupported_modes(self):
  m=metadata(2);m['active_channel_count']=3
  with self.assertRaises(FormatError):read_header(io.BytesIO(make_header(m)))
 def test_csv_and_wifi_only_enabled_channels(self):
  for count in (2,4):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);file=root/'trial.afolog';generate(file,count,duration=.04)
    report=convert(file,root/'csv',make_plots=False)
    self.assertTrue(report['no_detected_sample_loss'])
    header=(root/'csv'/'emg.csv').read_text().splitlines()[0]
    self.assertIn(f'ch{count-1}_raw',header);self.assertNotIn(f'ch{count}_raw',header)
    capture=Capture(root/'wifi');capture.accept(encode_packet(1,1,1,1,json.dumps(metadata(count)).encode()))
    capture.accept(encode_packet(2,1,1,2,frame(1,125,count),count=1))
    self.assertEqual(len(capture.snapshot()['emg'][0]),count+3);capture.close()
 def test_record_crc_fault(self):
  b=bytearray(frame(1,125,4));b[30]^=1
  with self.assertRaises(FormatError):decode_record(b)
 def test_fault_exports(self):
  for scenario in ('overflow','missing_emg','missing_imu','adc_crc_error','interrupted'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);generate(root/'x.afolog',4,scenario)
    report=convert(root/'x.afolog',root/'csv',make_plots=False,recover=scenario=='interrupted')
    self.assertFalse(report['no_detected_sample_loss'],scenario)
if __name__=='__main__':unittest.main()
