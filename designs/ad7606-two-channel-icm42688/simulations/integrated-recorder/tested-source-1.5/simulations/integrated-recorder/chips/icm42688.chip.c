// Register/FIFO subset for the recorder, not a manufacturer sensor model.
// 200Hz standard 16-byte packets, 1us rolling timestamp, independent chip timers.
#include "wokwi-api.h"
#include <stdlib.h>
#include <string.h>
typedef struct {pin_t cs,irq;spi_dev_t spi;timer_t tick,pulse;uint32_t fault,identity;
 uint8_t reg[128],fifo[2048],byte,addr;bool command,read,fifo_read;unsigned used,head;uint16_t stamp;} chip_t;
static void irq_low(void *p){chip_t *s=p;pin_write(s->irq,0);}
static void sample(void *p){
 chip_t *s=p;if(s->reg[0x16]!=0x40||s->reg[0x4e]!=0x0f)return;
 uint32_t fault=attr_read(s->fault);if(fault==1)return;
 s->stamp+=5000;
 uint8_t packet[16]={0x68,0,0,0,0,8,0,0,0,0,0,0,0,0,(uint8_t)(s->stamp>>8),(uint8_t)s->stamp};
 packet[2]=attr_read(s->identity); // foot/shank marker on accel X
 if(s->used+16<=2048){for(unsigned i=0;i<16;i++)s->fifo[(s->head+s->used+i)%2048]=packet[i];s->used+=16;}
 if(fault==2)s->used=2048;
 if(s->used==2048)s->reg[0x2d]|=2;
 if(fault!=3&&(s->reg[0x65]&8)){pin_write(s->irq,1);timer_start(s->pulse,10,false);}
}
static uint8_t next(chip_t *s){
 if(attr_read(s->fault)==1)return 0xff;
 unsigned a=s->addr;
 if(s->fifo_read){if(!s->used)return 0x80;return s->fifo[s->head];}
 s->addr=(a+1)&127;
 if(a==0x2e)return s->used>>8;if(a==0x2f)return s->used;
 uint8_t b=s->reg[a];if(a==0x2d)s->reg[a]=0;return b;
}
static void done(void *p,uint8_t *b,uint32_t n){
 chip_t *s=p;if(pin_read(s->cs)||!n)return;
 if(s->command){s->read=(*b&0x80)!=0;s->addr=*b&127;s->fifo_read=s->read&&s->addr==0x30;s->command=false;}
 else if(s->read){if(s->fifo_read&&s->used){s->head=(s->head+1)%2048;s->used--;}}
 else {unsigned a=s->addr++&127;
  if(a==0x11&&(*b&1)){memset(s->reg,0,128);s->reg[0x75]=0x47;s->used=s->head=0;}
  else{s->reg[a]=*b;if(a==0x4b&&(*b&2))s->used=s->head=0;}
 }
 s->byte=s->read?next(s):0;spi_start(s->spi,&s->byte,1);
}
static void cs(void *p,pin_t pin,uint32_t v){
 (void)pin;chip_t *s=p;if(v){spi_stop(s->spi);return;}s->command=true;s->byte=0;spi_start(s->spi,&s->byte,1);
}
void chip_init(void){
 chip_t *s=calloc(1,sizeof(*s));s->reg[0x75]=0x47;s->cs=pin_init("CS",INPUT_PULLUP);s->irq=pin_init("INT1",OUTPUT_LOW);s->fault=attr_init("fault",0);s->identity=attr_init("identity",1);
 spi_config_t spi={.sck=pin_init("SCLK",INPUT),.mosi=pin_init("SDI",INPUT),.miso=pin_init("SDO",INPUT),.mode=0,.done=done,.user_data=s};s->spi=spi_init(&spi);
 timer_config_t tick={.callback=sample,.user_data=s},pulse={.callback=irq_low,.user_data=s};s->tick=timer_init(&tick);s->pulse=timer_init(&pulse);timer_start(s->tick,5000,true);
 pin_watch_config_t watch={.edge=BOTH,.pin_change=cs,.user_data=s};pin_watch(s->cs,&watch);
}
