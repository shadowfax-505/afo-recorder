#include "format.h"
#include <string.h>
static uint32_t table[256];
void afo_format_init(void) {
    for (unsigned i=0;i<256;i++) {
        uint32_t c=i;
        for (int j=0;j<8;j++) c=(c>>1)^((c&1)?0xedb88320u:0);
        table[i]=c;
    }
}
uint32_t afo_crc32(const void *data, size_t len) {
    const uint8_t *p=data; uint32_t c=0xffffffffu;
    for(size_t i=0;i<len;i++) c=table[(c^p[i])&255]^(c>>8);
    return c^0xffffffffu;
}
void afo_record_init(afo_record_t *r, uint8_t type, uint8_t flags,
                     uint32_t seq, uint64_t time, const void *payload, size_t len) {
    memset(r,0,sizeof(*r)); r->magic=AFO_RECORD_MAGIC; r->type=type;
    r->flags=flags; r->sequence=seq; r->timestamp_us=time;
    if (len>40) len=40;
    r->payload_len=(uint16_t)len;
    memcpy(r->payload,payload,len);
    r->crc=afo_crc32(r,60);
}
int afo_header(void *buffer, const char *json) {
    size_t n=strlen(json); if(n>AFO_HEADER_BYTES-20) return -1;
    uint8_t *b=buffer; memset(b,0,AFO_HEADER_BYTES);
    memcpy(b,"AFOLOG1\0",8);
    uint16_t version=1, size=AFO_HEADER_BYTES; uint32_t len=n;
    memcpy(b+8,&version,2); memcpy(b+10,&size,2); memcpy(b+12,&len,4);
    memcpy(b+16,json,n); uint32_t crc=afo_crc32(b,AFO_HEADER_BYTES-4);
    memcpy(b+AFO_HEADER_BYTES-4,&crc,4); return 0;
}
