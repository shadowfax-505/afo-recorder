#include "format.h"
#include "board.h"
#include "ads_crc.h"
#include <stdio.h>
int main(void) {
    afo_format_init();
    if(afo_crc32("123456789",9)!=0xcbf43926u)return 1;
    if(ads_crc16((const unsigned char*)"123456789",9)!=0x29b1)return 2;
    unsigned char f[18]={1,15,0,0x7f,0xff,0xff,0x80,0,0,0xff,0xff,0xff,0,0,1};
    uint16_t crc=ads_crc16(f,15),status,out_crc;f[15]=crc>>8;f[16]=crc;
    int32_t codes[4];
    if(ads_decode24(f,codes,&status,&out_crc)||codes[0]!=8388607||codes[1]!=-8388608||codes[2]!=-1||codes[3]!=1)return 3;
    f[8]^=1;if(ads_decode24(f,codes,&status,&out_crc)!=1)return 4;f[8]^=1;
    f[0]|=4;crc=ads_crc16(f,15);f[15]=crc>>8;f[16]=crc;
    if(ads_decode24(f,codes,&status,&out_crc)!=2)return 5;
    emg_payload_t p={.codes={123456,-765432,0,0},.adc_status=0x103,.adc_crc=0x4321,.read_duration_us=18,.elapsed_slots=1,.active_mask=(1<<EMG_CHANNEL_COUNT)-1,.read_start_us=123456792};
    if(EMG_CHANNEL_COUNT==4){p.codes[2]=-1;p.codes[3]=8388607;p.adc_status=0x10f;}
    #if AFO_AD7606
    p.codes[0]=32767;p.codes[1]=-32768;p.codes[2]=EMG_CHANNEL_COUNT==4?-1:0;p.codes[3]=EMG_CHANNEL_COUNT==4?1234:0;p.adc_status=0;p.adc_crc=0;
#endif
    afo_record_t r;afo_record_init(&r,AFO_EMG_RECORD_KIND,0,42,123456789,&p,sizeof(p));
    return fwrite(&r,1,sizeof(r),stdout)==sizeof(r)?0:6;
}
