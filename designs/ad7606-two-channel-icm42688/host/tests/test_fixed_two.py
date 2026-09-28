"""Fixed-two hardware contract; shared readers deliberately retain legacy four-channel support."""
from pathlib import Path
import json,subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
class FixedTwoTests(unittest.TestCase):
 def test_only_two_input_circuits(self):
  parts={p['ref']:p for p in json.loads((ROOT/'design/main.json').read_text())['parts']}
  self.assertTrue({'J5','J6'}<=parts.keys());self.assertFalse({'J7','J8'}&parts.keys())
  for pin in [53,55,57,59,61,63]:self.assertEqual(parts['U2']['pins'][str(pin)],'GND')
  for p in parts.values():
   for net in p['pins'].values():self.assertFalse(net and net.startswith(('RAW2','RAW3','RC2','RC3','BUF2','BUF3')))
 def test_unused_amplifiers_terminated(self):
  parts={p['ref']:p for p in json.loads((ROOT/'design/main.json').read_text())['parts']}
  for ref in ['U3','U4']:
   pins=parts[ref]['pins'];self.assertEqual(pins['10'],'GND');self.assertEqual(pins['12'],'GND');self.assertEqual(pins['8'],pins['9']);self.assertEqual(pins['13'],pins['14'])
 def test_four_channel_firmware_rejected(self):
  # Preprocess board.h directly; this tests the actual firmware guard without ESP-IDF.
  result=subprocess.run(['cc','-E','-x','c','-DEMG_CHANNEL_COUNT=4','-include',str(ROOT/'firmware/main/board.h'),'-'],input='',text=True,capture_output=True)
  self.assertNotEqual(result.returncode,0);self.assertIn('exactly two EMG inputs',result.stderr)
if __name__=='__main__':unittest.main()
