#include "ads_crc.h"
uint16_t ads_crc16(const uint8_t *data,size_t length) {
    uint16_t crc=0xffff;
    while(length--) {
        crc^=(uint16_t)*data++<<8;
        for(int bit=0;bit<8;bit++)crc=(crc&0x8000)?(crc<<1)^0x1021:crc<<1;
    }
    return crc;
}
int ads_decode24(const uint8_t f[18],int32_t codes[4],uint16_t *status,uint16_t *crc) {
    *status=((uint16_t)f[0]<<8)|f[1];*crc=((uint16_t)f[15]<<8)|f[16];
    if(ads_crc16(f,15)!=*crc)return 1;
    if((*status&0x5400)||(*status&0x0300)!=0x0100)return 2;
    for(unsigned i=0;i<4;i++) {
        uint32_t u=((uint32_t)f[3+3*i]<<16)|((uint32_t)f[4+3*i]<<8)|f[5+3*i];
        codes[i]=(u&0x800000)?(int32_t)u-0x1000000:(int32_t)u;
    }
    return 0;
}
