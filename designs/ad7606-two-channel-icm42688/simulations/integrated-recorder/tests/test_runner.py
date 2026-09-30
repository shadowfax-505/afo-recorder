import base64
import binascii
import gzip
import importlib.util
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

P=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('integrated_runner',P/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

def exported(kind,raw):
    return f'EXPORT,{kind},0,{base64.b64encode(raw).decode()}\nEXPORT_END,{kind},{len(raw)}\n'

class EvidenceTests(unittest.TestCase):
    def test_contiguous_export(self):
        self.assertEqual(runner.extract(exported('AFO',b'123'),'AFO'),b'123')
    def test_missing_end(self):
        with self.assertRaises(ValueError):runner.extract('EXPORT,AFO,0,MTIz\n','AFO')
    def test_duplicate_end(self):
        with self.assertRaises(ValueError):runner.extract(exported('AFO',b'123')+'EXPORT_END,AFO,3\n','AFO')
    def test_incomplete_export(self):
        with self.assertRaises(ValueError):runner.extract('EXPORT,AFO,0,MTIz\nEXPORT_END,AFO,4\n','AFO')
    def test_noncontiguous_offset(self):
        with self.assertRaises(ValueError):runner.extract('EXPORT,AFO,1,MTIz\nEXPORT_END,AFO,3\n','AFO')
    def test_invalid_base64(self):
        with self.assertRaises(ValueError):runner.extract('EXPORT,AFO,0,A\nEXPORT_END,AFO,3\n','AFO')
    def test_short_udp_length(self):
        with self.assertRaises(ValueError):runner.packet_list(b'\x01')
    def test_short_udp_payload(self):
        with self.assertRaises(ValueError):runner.packet_list(b'\x03\x00x')
    def test_no_false_pass_without_completion(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ValueError):runner.assess('normal','',Path(name))
    def test_panic_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ValueError):runner.assess('normal',
                'assert failed: xQueueSemaphoreTake\nINTEGRATED_COMPLETE,case=0,\n',Path(name))
    def test_genuine_normal_capture(self):
        text=gzip.decompress((P/'results/current/normal/serial.txt.gz').read_bytes()).decode()
        with tempfile.TemporaryDirectory() as name:
            result=runner.assess('normal',text,Path(name))
            self.assertTrue(result['pass']);self.assertEqual(result['quality']['counts']['emg'],10041)
    def test_plausible_wrong_code_rejected(self):
        text=gzip.decompress((P/'results/current/normal/serial.txt.gz').read_bytes()).decode()
        raw=bytearray(runner.extract(text,'AFO'))
        # Change one real ADC reading to a plausible -1 code, recomputing its CRC.
        start=runner.HEADER_SIZE
        while raw[start+4]!=7:start+=64
        struct.pack_into('<i',raw,start+20,-1)
        struct.pack_into('<I',raw,start+60,binascii.crc32(raw[start:start+60])&0xffffffff)
        prefix='\n'.join(x for x in text.splitlines() if not x.startswith(('EXPORT,','EXPORT_END,')))+'\n'
        altered=prefix+exported('AFO',raw)+exported('UDP',runner.extract(text,'UDP'))
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaisesRegex(ValueError,'ADC code/channel mismatch'):
                runner.assess('normal',altered,Path(name))
    def test_packet_loss_does_not_invent_end(self):
        text=gzip.decompress((P/'results/current/wireless-packet-loss/serial.txt.gz').read_bytes()).decode()
        with tempfile.TemporaryDirectory() as name:
            result=runner.assess('wireless-packet-loss',text,Path(name))
            self.assertTrue(result['pass']);self.assertFalse(result['live']['ended'])
            self.assertIsNone(result['live']['stop_reason']);self.assertEqual(result['live']['stats']['packet_gaps'],158)
    def test_quota_is_not_a_firmware_failure_or_pass(self):
        def quota(cmd,stdout,**kwargs):
            stdout.write('API Error: You have used up your Free plan monthly CI minute quota.\n')
            return subprocess.CompletedProcess(cmd,1)
        with tempfile.TemporaryDirectory() as name:
            result=runner.run_case('normal',Path(name)/'fresh',execute=quota)
            self.assertIsNone(result['pass']);self.assertEqual(result['status'],'not_run_quota')

    def test_unconfirmed_conversion_fault_models(self):
        for case,fault in [('adc-busy-stays-low','4'),('adc-trigger-ignored','5')]:
            with self.subTest(case=case):
                diagram=runner.make_diagram(case)
                adc=next(x for x in diagram['parts'] if x['id']=='adc')
                self.assertEqual(adc['attrs']['fault'],fault)

    def test_unconfirmed_conversion_rejects_plausible_measurement(self):
        stopped=gzip.decompress((P/'results/current/adc-stuck-busy/serial.txt.gz').read_bytes()).decode()
        nominal=gzip.decompress((P/'results/current/normal/serial.txt.gz').read_bytes()).decode()
        raw=runner.extract(stopped,'AFO');valid=runner.extract(nominal,'AFO')
        pos=runner.HEADER_SIZE
        while valid[pos+4]!=7:pos+=runner.RECORD_SIZE
        # Inject a CRC-valid, known-code record into an unaccepted-trigger fault.
        altered=raw[:runner.HEADER_SIZE]+valid[pos:pos+runner.RECORD_SIZE]+raw[runner.HEADER_SIZE:]
        prefix='\n'.join(x for x in stopped.splitlines() if not x.startswith(('EXPORT,','EXPORT_END,')))+'\n'
        serial=prefix+exported('AFO',altered)+exported('UDP',runner.extract(stopped,'UDP'))
        for case in ('adc-busy-stays-low','adc-trigger-ignored'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as name:
                result=runner.assess(case,serial,Path(name))
                self.assertFalse(result['pass'])
                self.assertIn('unconfirmed conversion accepted plausible EMG data',result['failures'])

if __name__=='__main__':unittest.main()
