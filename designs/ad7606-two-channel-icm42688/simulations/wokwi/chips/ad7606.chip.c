// Behavioral ORIGINAL AD7606: no register map or sensor-frame CRC.
// SPI mode 2, eight signed 16-bit words through DOUTA. No analog physics.
#include "wokwi-api.h"
#include <stdlib.h>
typedef struct {pin_t cs,conv,busy,reset;spi_dev_t spi;timer_t timer;uint32_t fault;uint8_t data[16];} chip_t;
static void ready(void *p){chip_t *s=p;pin_write(s->busy,0);}
static void done(void *p,uint8_t *b,uint32_t n){(void)p;(void)b;(void)n;}
static void edge(void *p,pin_t pin,uint32_t v){
 chip_t *s=p;
 if(pin==s->reset&&v){timer_stop(s->timer);pin_write(s->busy,0);return;}
 if(pin==s->conv&&v){
  if(pin_read(s->busy))return;
  pin_write(s->busy,1);
  uint32_t fault=attr_read(s->fault);
  if(fault!=1)timer_start(s->timer,fault==2?250:4,false);
 }
 if(pin==s->cs){
  if(v){spi_stop(s->spi);return;}
  // Distinct values expose byte order, sign and eight-word readout errors.
  const int16_t codes[8]={6554,13107,-1234,2345,-32768,32767,0,1111};
  for(unsigned i=0;i<8;i++){uint16_t u=codes[i];s->data[2*i]=u>>8;s->data[2*i+1]=u;}
  if(attr_read(s->fault)==3)for(unsigned i=0;i<16;i++)s->data[i]=0xff; // parallel strap: no serial data
  spi_start(s->spi,s->data,16);
 }
}
void chip_init(void){
 chip_t *s=calloc(1,sizeof(*s));s->cs=pin_init("CS",INPUT_PULLUP);s->conv=pin_init("CONVST",INPUT);s->reset=pin_init("RESET",INPUT);s->busy=pin_init("BUSY",OUTPUT_LOW);s->fault=attr_init("fault",0);
 spi_config_t spi={.sck=pin_init("SCLK",INPUT),.mosi=NO_PIN,.miso=pin_init("DOUTA",INPUT),.mode=2,.done=done,.user_data=s};s->spi=spi_init(&spi);
 timer_config_t timer={.callback=ready,.user_data=s};s->timer=timer_init(&timer);
 pin_watch_config_t watch={.edge=BOTH,.pin_change=edge,.user_data=s};pin_watch(s->cs,&watch);pin_watch(s->conv,&watch);pin_watch(s->reset,&watch);
}
