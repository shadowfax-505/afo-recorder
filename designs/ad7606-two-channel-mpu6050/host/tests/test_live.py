import io,json,tempfile,unittest
from pathlib import Path
from afo_format import EMG,make_record,read_header,FormatError
from generate_example import generate
from live_protocol import encode_packet,decode_packet
from live_receiver import Capture

class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();p=Path(self.temp.name)
        example=p/'source.afolog';generate(example,.01)
        with example.open('rb') as f:self.meta=read_header(f)
        self.capture=Capture(p/'capture');self.seq=0
    def tearDown(self):self.capture.close();self.temp.cleanup()
    def packet(self,kind,payload,count=0,session=1):
        self.seq+=1;return encode_packet(kind,10,session,self.seq,payload,count)
    def header(self,session=1):self.capture.accept(self.packet(1,json.dumps(self.meta).encode(),session=session))
    def record(self,n=1):return make_record(1,n,1000000+n*125,EMG.pack(2048,2000,25,27,25,1))
    def test_framing_and_original_record(self):
        raw=self.record();p=decode_packet(encode_packet(2,10,1,3,raw,1));self.assertEqual(p['payload'],raw);self.assertEqual(p['records'][0].sequence,1)
    def test_bad_packet_crc_rejected(self):
        packet=bytearray(self.packet(2,self.record(),1));packet[-1]^=1
        with self.assertRaises(FormatError):decode_packet(packet)
        self.capture.accept(packet);self.assertEqual(self.capture.stats['invalid_packets'],1)
    def test_record_crc_checked_inside_valid_packet(self):
        raw=bytearray(self.record());raw[-1]^=1
        with self.assertRaises(FormatError):decode_packet(self.packet(2,raw,1))
    def test_missing_and_duplicate_packets_visible(self):
        self.header();self.seq+=1;p=self.packet(2,self.record(),1);self.capture.accept(p);self.capture.accept(p)
        self.assertEqual(self.capture.stats['packet_gaps'],1);self.assertEqual(self.capture.stats['reordered_or_duplicate'],1)
        self.assertEqual(self.capture.snapshot()['records'],1)
    def test_unknown_session_never_guesses_metadata(self):
        self.capture.accept(self.packet(2,self.record(),1));self.assertEqual(self.capture.stats['unknown_session_packets'],1);self.assertIsNone(self.capture.current)
    def test_new_session_separate_file_and_voltage(self):
        self.header();self.capture.accept(self.packet(2,self.record(),1));self.header(2)
        self.capture.accept(self.packet(2,self.record(2),1,session=2))
        self.assertEqual(len(self.capture.sessions),2);self.assertEqual(self.capture.snapshot()['emg'][0][1],1.65)
    def test_sample_gap_visible(self):
        self.header();self.capture.accept(self.packet(2,self.record(1)+self.record(3),2))
        self.assertEqual(self.capture.snapshot()['sequence_gaps'][1],1)
    def test_bad_lengths_and_counts(self):
        with self.assertRaises(FormatError):decode_packet(self.packet(2,self.record(),2))
        with self.assertRaises(FormatError):decode_packet(b'bad')
    def test_sequence_wrap(self):
        self.header();self.capture.last_packet[10]=0xffffffff
        self.capture.accept(encode_packet(2,10,1,0,self.record(),1))
        self.assertEqual(self.capture.stats['packet_gaps'],0);self.assertEqual(self.capture.snapshot()['records'],1)
if __name__=='__main__':unittest.main()
