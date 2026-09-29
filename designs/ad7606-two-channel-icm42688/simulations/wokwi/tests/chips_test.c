// Native unit tests of the actual custom-chip C source. NOT ESP32 execution.
#include "../chips/wokwi-api.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned levels[32],pin_n,attr_n,attrs[16],timer_n;
static pin_watch_config_t watches[32];static timer_config_t timers[8];
static unsigned durations[8];static bool active[8];
static spi_config_t bus;static uint8_t *transfer;static uint32_t transfer_n;
pin_t pin_init(const char *n,uint32_t mode){(void)n;pin_t p=pin_n++;levels[p]=(mode==INPUT_PULLUP||mode==OUTPUT_HIGH);return p;}
uint32_t pin_read(pin_t p){return levels[p];}
void pin_write(pin_t p,uint32_t v){levels[p]=v;}
bool pin_watch(pin_t p,const pin_watch_config_t *w){watches[p]=*w;return true;}
spi_dev_t spi_init(const spi_config_t *c){bus=*c;return 1;}
void spi_start(spi_dev_t s,uint8_t *p,uint32_t n){(void)s;transfer=p;transfer_n=n;}
void spi_stop(spi_dev_t s){(void)s;transfer=NULL;transfer_n=0;}
uint32_t attr_init(const char *n,uint32_t v){(void)n;attrs[attr_n]=v;return attr_n++;}
uint32_t attr_read(uint32_t a){return attrs[a];}
timer_t timer_init(const timer_config_t *c){timers[timer_n]=*c;return timer_n++;}
void timer_start(timer_t t,uint32_t us,bool repeat){durations[t]=us;active[t]=true;(void)repeat;}
void timer_stop(timer_t t){active[t]=false;}
static void drive(pin_t p,unsigned v){levels[p]=v;watches[p].pin_change(watches[p].user_data,p,v);}
#ifdef ADC_MODEL
#include "../chips/ad7606.chip.c"
int main(void){
 chip_init();chip_t *s=bus.user_data;assert(bus.mode==2);
 drive(s->conv,1);assert(pin_read(s->busy));assert(durations[s->timer]==4);ready(s);assert(!pin_read(s->busy));drive(s->cs,0);assert(transfer_n==16);
 int16_t expected[8]={6554,13107,-1234,2345,-32768,32767,0,1111};
 for(unsigned i=0;i<8;i++)assert((int16_t)((transfer[2*i]<<8)|transfer[2*i+1])==expected[i]);
 drive(s->cs,1);attrs[s->fault]=3;drive(s->cs,0);for(unsigned i=0;i<16;i++)assert(transfer[i]==255);
 drive(s->reset,1);assert(!pin_read(s->busy));
 attrs[s->fault]=1;drive(s->conv,1);assert(pin_read(s->busy)&&!active[s->timer]);
 drive(s->reset,1);attrs[s->fault]=2;drive(s->conv,1);assert(pin_read(s->busy)&&durations[s->timer]==250);
 puts("PASS AD7606 model: 8-word order, signed codes, serial-mode fault, reset, BUSY");return 0;
}
#else
#include "../chips/icm42688.chip.c"
static uint8_t byte(uint8_t tx){assert(transfer_n==1);uint8_t rx=*transfer;*transfer=tx;bus.done(bus.user_data,transfer,1);return rx;}
static void write_reg(chip_t *s,uint8_t a,uint8_t v){drive(s->cs,0);byte(a);byte(v);drive(s->cs,1);}
static uint8_t read_reg(chip_t *s,uint8_t a){drive(s->cs,0);byte(a|128);uint8_t v=byte(0);drive(s->cs,1);return v;}
int main(void){
 chip_init();chip_t *s=bus.user_data;assert(bus.mode==0);assert(read_reg(s,0x75)==0x47);
 write_reg(s,0x4e,0x0f);write_reg(s,0x16,0x40);write_reg(s,0x65,8);
 sample(s);sample(s);assert(s->used==32);assert(pin_read(s->irq));irq_low(s);assert(!pin_read(s->irq));
 drive(s->cs,0);byte(0xae);assert(byte(0)==0);assert(byte(0)==32);drive(s->cs,1);assert(s->used==32);
 drive(s->cs,0);byte(0xb0);uint8_t packet[16];for(unsigned i=0;i<16;i++)packet[i]=byte(0);drive(s->cs,1);
 assert(s->used==16);assert(packet[0]==0x68&&packet[2]==1&&packet[5]==8&&packet[14]==(5000>>8)&&packet[15]==(5000&255));
 attrs[s->fault]=3;sample(s);assert(!pin_read(s->irq));attrs[s->fault]=2;sample(s);assert(read_reg(s,0x2d)&2);
 write_reg(s,0x4b,2);assert(s->used==0);attrs[s->fault]=1;assert(read_reg(s,0x75)==255);
 puts("PASS ICM model: identity/readback, FIFO byte order, no prefetched-byte loss, overflow, absent sensor, missed interrupt");return 0;
}
#endif
