"""Firmware limits that a host compiler can check without ESP-IDF."""
from pathlib import Path
import json,re,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[2]
MAIN=ROOT/'firmware/main'
sys.path.insert(0,str(ROOT/'host'))
import live_protocol
def macros(*flags):
    out=subprocess.run(['cc','-E','-dM','-x','c',*flags,str(MAIN/'board.h')],text=True,capture_output=True,check=True).stdout
    return dict(re.findall(r'^#define (\w+) (.+)$',out,re.M))
class FirmwareLimitTests(unittest.TestCase):
    def metadata(self,channels,hardware):
        text=(MAIN/'main.c').read_text()
        start=text.index('snprintf(meta,sizeof(meta),')
        end=text.index(');',text.index('EMG_CHANNEL_COUNT==2?',start))
        args=text[start+len('snprintf(meta,sizeof(meta),'):end].replace("strrchr(path,'/')+1",'"trial_deadbeef.afolog"')
        extra='#include "imu_tick.h"\n' if (MAIN/'imu_tick.h').exists() else ''
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'probe.c';binary=Path(temp)/'probe'
            source.write_text('#include <stdio.h>\n#include <string.h>\n#include "board.h"\n'+extra+
                'int main(void){char meta[4096];int n=(snprintf)(meta,sizeof(meta),'+args+');printf("%d\\n%s",n,meta);return 0;}\n')
            subprocess.run(['cc','-w',f'-DEMG_CHANNEL_COUNT={channels}',f'-DAFO_BREADBOARD={int(hardware=="breadboard")}',
                            f'-DHARDWARE_VARIANT="{hardware}"','-I',str(MAIN),'-o',str(binary),str(source)],check=True,capture_output=True)
            length,body=subprocess.run([str(binary)],text=True,capture_output=True,check=True).stdout.split('\n',1)
        return int(length),json.loads(body)
    def test_session_metadata_fits_live_limit(self):
        limit=int(macros()['WIFI_LIVE_METADATA_MAX'])
        self.assertEqual(limit,live_protocol.MAX_PAYLOAD)
        self.assertLessEqual(limit+32,2048,'host receivers read 2,048-byte datagrams')
        counts=[2] if 'two-channel' in ROOT.name else [2,4]
        for channels in counts:
            for hardware in ('breadboard','pcb'):
                length,meta=self.metadata(channels,hardware)
                # Exceeding the limit silently disables the live preview.
                self.assertLessEqual(length,limit-32,(channels,hardware,length))
                self.assertEqual(meta['active_channel_count'],channels)
    def test_record_queue_outlasts_sd_write_busy(self):
        self.assertGreaterEqual(int(macros()['RECORD_QUEUE_LENGTH'])/8400,2.0)
        self.assertIn('MALLOC_CAP_SPIRAM',(MAIN/'main.c').read_text())
    def test_no_wifi_password_in_firmware_source(self):
        for name in ('board.h','wifi_live.c','main.c'):
            text=(MAIN/name).read_text()
            self.assertNotIn('AFO-Bench-2026',text);self.assertIsNone(re.search(r'#define\s+WIFI_LIVE_PASSWORD\s+"',text))
        self.assertIn('nvs_set_str',(MAIN/'wifi_live.c').read_text())
if __name__=='__main__':unittest.main()
