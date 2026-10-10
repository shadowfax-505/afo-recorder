"""Fixed-two hardware contract; shared readers deliberately retain legacy four-channel support."""
from pathlib import Path
import json,re,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host'))
import live_protocol
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
def board_macros():
 result=subprocess.run(['cc','-E','-dM','-x','c','-DAFO_BREADBOARD=1',str(ROOT/'firmware/main/board.h')],text=True,capture_output=True,check=True)
 return dict(re.findall(r'^#define (\w+) (.+)$',result.stdout,re.M))
class FirmwareLimitTests(unittest.TestCase):
 def metadata(self,hardware):
  with tempfile.TemporaryDirectory() as temp:
   main=Path(temp)/'probe.c';binary=Path(temp)/'probe'
   main.write_text('#include <stdio.h>\n#include "metadata.h"\nint main(void){char m[4096];int n=afo_session_metadata(m,sizeof m,"trial_deadbeef.afolog");printf("%d\\n%s",n,m);return 0;}\n')
   subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',f'-DHARDWARE_VARIANT="{hardware}"',f'-DAFO_BREADBOARD={int(hardware=="breadboard")}',
                   '-I',str(ROOT/'firmware/main'),'-o',str(binary),str(main),str(ROOT/'firmware/main/metadata.c')],check=True,capture_output=True)
   length,text=subprocess.run([str(binary)],text=True,capture_output=True,check=True).stdout.split('\n',1)
  return int(length),text
 def test_session_metadata_fits_live_packet_and_header(self):
  macros=board_macros();limit=int(macros['WIFI_LIVE_METADATA_MAX'])
  self.assertEqual(limit,live_protocol.MAX_PAYLOAD)
  self.assertLessEqual(limit+32,1472,'metadata packet must fit one 1500-byte MTU without IP fragmentation')
  for hardware in ('breadboard','pcb'):
   length,text=self.metadata(hardware);meta=json.loads(text)
   self.assertEqual(length,len(text))
   # Keep deliberate headroom: growing metadata past the limit silently disables the live preview.
   self.assertLessEqual(length,limit-64,(hardware,length))
   self.assertLessEqual(length,4096-20)
   self.assertEqual(meta['firmware'],json.loads(macros['AFO_FIRMWARE_ID']))
   self.assertEqual(meta['hardware_variant'],hardware)
   self.assertEqual(meta['record_queue_entries'],int(macros['RECORD_QUEUE_LENGTH']))
 def test_record_queue_outlasts_sd_write_busy(self):
  # SD write busy may reach 500 ms (SDXC); keep at least 2 s at 8,000 EMG + 400 IMU records/s.
  self.assertGreaterEqual(int(board_macros()['RECORD_QUEUE_LENGTH'])/8400,2.0)
  self.assertIn('MALLOC_CAP_SPIRAM',(ROOT/'firmware/main/main.c').read_text())
 def test_no_wifi_password_in_firmware_source(self):
  for name in ('board.h','wifi_live.c','main.c'):
   text=(ROOT/'firmware/main'/name).read_text()
   self.assertNotIn('AFO-Bench-2026',text);self.assertIsNone(re.search(r'#define\s+WIFI_LIVE_PASSWORD\s+"',text))
  self.assertIn('nvs_set_str',(ROOT/'firmware/main/wifi_live.c').read_text())
if __name__=='__main__':unittest.main()
