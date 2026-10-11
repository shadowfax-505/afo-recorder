#include "icm42688_model.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
enum {DEVICE_CONFIG=0x11,INT_CONFIG=0x14,FIFO_CONFIG=0x16,INT_STATUS=0x2D,FIFO_COUNTH=0x2E,FIFO_COUNTL=0x2F,FIFO_DATA=0x30,
      SIGNAL_PATH_RESET=0x4B,INTF_CONFIG0=0x4C,INTF_CONFIG1=0x4D,PWR_MGMT0=0x4E,GYRO_CONFIG0=0x4F,ACCEL_CONFIG0=0x50,
      GYRO_CONFIG1=0x51,GYRO_ACCEL_CONFIG0=0x52,ACCEL_CONFIG1=0x53,TMST_CONFIG=0x54,FIFO_CONFIG1=0x5F,INT_CONFIG1=0x64,
      INT_SOURCE0=0x65,WHO_AM_I=0x75,REG_BANK_SEL=0x76};
/* Reset values and reserved-bit masks (DS-000347 section 14). */
static const struct {uint8_t addr,reset,reserved;} RESET[]={
    {DEVICE_CONFIG,0x00,0xEE},{INT_CONFIG,0x00,0xC0},{FIFO_CONFIG,0x00,0x3F},{INT_STATUS,0x10,0x80},
    {SIGNAL_PATH_RESET,0x00,0x91},{INTF_CONFIG0,0x30,0x0C},{INTF_CONFIG1,0x91,0x00},{PWR_MGMT0,0x00,0xC0},
    {GYRO_CONFIG0,0x06,0x10},{ACCEL_CONFIG0,0x06,0x10},{GYRO_CONFIG1,0x16,0x10},{GYRO_ACCEL_CONFIG0,0x11,0x00},
    {ACCEL_CONFIG1,0x0D,0xE1},{TMST_CONFIG,0x23,0xE0},{FIFO_CONFIG1,0x00,0x80},{INT_CONFIG1,0x10,0x8F},
    {INT_SOURCE0,0x10,0x80},{WHO_AM_I,0x47,0x00},{REG_BANK_SEL,0x00,0xF8}};
void icm_violation(icm_model_t *m,const char *what){
    m->violations++;snprintf(m->last_violation,sizeof m->last_violation,"%s: %s at %.1f us",m->name,what,m->now_us);
    fprintf(stderr,"VIOLATION %s\n",m->last_violation);
}
static void soft_reset(icm_model_t *m){
    memset(m->reg,0,sizeof m->reg);
    for(size_t i=0;i<sizeof RESET/sizeof RESET[0];i++)m->reg[RESET[i].addr]=RESET[i].reset;
    m->used=0;m->count_latched=false;m->gyro_on_us=m->accel_on_us=-1;m->tick=0;m->tick_acc=0;
}
void icm_init(icm_model_t *m,const char *name,double clock_ppm){
    memset(m,0,sizeof *m);m->name=name;m->clock_ppm=clock_ppm;m->stuck_addr=-1;
    m->period_us=5000*(1+clock_ppm*1e-6);soft_reset(m);
    m->reset_until_us=1000; /* 1 ms start-up time for register access after power-up */
    m->accel[2]=2048;m->temperature=25;
}
static bool streaming(const icm_model_t *m){
    return (m->reg[PWR_MGMT0]&0x0C)==0x0C&&(m->reg[PWR_MGMT0]&0x03)==0x03&&(m->reg[FIFO_CONFIG]>>6)==1;
}
static void put16(uint8_t *p,int16_t v,bool big){uint16_t u=(uint16_t)v;if(big){p[0]=u>>8;p[1]=u;}else{p[0]=u;p[1]=u>>8;}}
static void produce(icm_model_t *m,double t){
    bool gyro_on=(m->reg[PWR_MGMT0]&0x0C)==0x0C,accel_on=(m->reg[PWR_MGMT0]&0x03)==0x03;
    if(!gyro_on&&!accel_on)return;
    /* Timestamp counter: 1 us mode ticks at 32/30 us (PLL 19.2 MHz); 16 us mode is 16 ticks of that. */
    /* ODR and timestamp share the sensor oscillator: 5000 sensor-us per sample whatever its error. */
    m->tick_acc+=5000.0*30.0/32.0/((m->reg[TMST_CONFIG]&0x08)?16:1);
    m->tick=(uint16_t)(uint64_t)m->tick_acc;
    m->reg[INT_STATUS]|=0x08; /* DATA_RDY */
    if(m->reg[INT_SOURCE0]&0x08){
        if(m->reg[INT_CONFIG1]&0x10)icm_violation(m,"INT1 used while INT_ASYNC_RESET=1 (datasheet: clear for proper INT pin operation)");
        if((m->reg[INT_CONFIG]&0x03)!=0x03)icm_violation(m,"INT1 not push-pull active-high; ESP32 rising-edge input without pull-up would miss it");
        if(m->irq_count<sizeof m->irq_times/sizeof m->irq_times[0])m->irq_times[m->irq_count++]=t;
    }
    if(!streaming(m))return;
    uint8_t c1=m->reg[FIFO_CONFIG1];
    if((c1&0x03)!=0x03){icm_violation(m,"FIFO stream enabled without both accel and gyro packets");return;}
    bool big=m->reg[INTF_CONFIG0]&0x10;uint8_t p[16]={0};
    p[0]=0x40|0x20|((m->reg[TMST_CONFIG]&0x01)?0x08:0x00); /* header: accel, gyro, ODR timestamp */
    bool accel_valid=t-m->accel_on_us>=10000,gyro_valid=t-m->gyro_on_us>=30000;
    for(int i=0;i<3;i++){put16(p+1+2*i,accel_valid?m->accel[i]:-32768,big);put16(p+7+2*i,gyro_valid?m->gyro[i]:-32768,big);}
    p[13]=(uint8_t)m->temperature;put16(p+14,(int16_t)m->tick,big);
    if(m->used+16>sizeof m->fifo){m->reg[INT_STATUS]|=0x02;memmove(m->fifo,m->fifo+16,m->used-16);m->used-=16;
        memmove(m->fifo_times,m->fifo_times+1,sizeof(double)*(m->used/16));}
    memcpy(m->fifo+m->used,p,16);m->fifo_times[m->used/16]=t;m->used+=16;
    if(m->samples<sizeof m->sample_times/sizeof m->sample_times[0])m->sample_times[m->samples++]=t;
}
void icm_advance(icm_model_t *m,double now_us){
    while(m->next_odr_us&&m->next_odr_us<=now_us){m->now_us=m->next_odr_us;produce(m,m->next_odr_us);m->next_odr_us+=m->period_us;}
    m->now_us=now_us;
}
static uint8_t read_reg(icm_model_t *m,uint8_t a){
    if(a==INT_STATUS){uint8_t v=m->reg[a];m->reg[a]=0;return v;}
    if(a==FIFO_COUNTH){m->latched_count=(uint16_t)m->used;m->count_latched=true;
        return (m->reg[INTF_CONFIG0]&0x20)?m->latched_count>>8:m->latched_count&0xff;}
    if(a==FIFO_COUNTL){if(!m->count_latched)icm_violation(m,"FIFO_COUNTL read without FIFO_COUNTH in the same burst");
        m->count_latched=false;return (m->reg[INTF_CONFIG0]&0x20)?m->latched_count&0xff:m->latched_count>>8;}
    return m->reg[a];
}
static void write_reg(icm_model_t *m,uint8_t a,uint8_t v){
    if(m->now_us<m->write_blackout_until_us)icm_violation(m,"register write within 200 us after enabling accel/gyro");
    if(a==m->stuck_addr)return;
    for(size_t i=0;i<sizeof RESET/sizeof RESET[0];i++)if(RESET[i].addr==a&&((v^RESET[i].reset)&RESET[i].reserved)&&a!=SIGNAL_PATH_RESET)
        icm_violation(m,"write changes reserved bits");
    switch(a){
    case DEVICE_CONFIG:
        if(v&0x10)icm_violation(m,"SPI_MODE=1 selects modes 1/2; driver uses mode 0");
        if(v&0x01){soft_reset(m);m->reset_until_us=m->now_us+1000;return;}break;
    case INTF_CONFIG0: if((v&0x03)<2)icm_violation(m,"UI_SIFS_CFG reserved code");break;
    case GYRO_CONFIG0: {int odr=v&0x0F;if(odr==0||(odr>=12&&odr<=14))icm_violation(m,"reserved GYRO_ODR");break;}
    case ACCEL_CONFIG0: {int odr=v&0x0F,fs=v>>5;if(odr==0||fs>=4)icm_violation(m,"reserved ACCEL_ODR/FS");
        if(odr>=12&&odr<=14)icm_violation(m,"LP-only ACCEL_ODR in LN mode");break;}
    case GYRO_CONFIG1: if((v&0x03)!=0x02||((v>>2)&3)==3)icm_violation(m,"reserved gyro filter order");break;
    case ACCEL_CONFIG1: if(((v>>1)&3)!=2||((v>>3)&3)==3)icm_violation(m,"reserved accel filter order");break;
    case GYRO_ACCEL_CONFIG0: {int a1=v>>4,g=v&0x0F;if((a1>=8&&a1<=13)||(g>=8&&g<=13))icm_violation(m,"reserved UI filter bandwidth");break;}
    case PWR_MGMT0: {
        bool g0=(m->reg[a]&0x0C)!=0,a0=(m->reg[a]&0x03)>1,g1=(v&0x0C)!=0,a1=(v&0x03)>1;
        if(((v>>2)&3)==2)icm_violation(m,"reserved GYRO_MODE");
        if((!g0&&g1)||(!a0&&a1))m->write_blackout_until_us=m->now_us+200;
        if(!g0&&g1)m->gyro_on_us=m->now_us;
        if(!a0&&a1)m->accel_on_us=m->now_us;
        if(g0&&!g1&&m->now_us-m->gyro_on_us<45000)icm_violation(m,"gyro turned off before the 45 ms minimum on-time");
        if((g1||a1)&&!m->next_odr_us)m->next_odr_us=m->now_us+m->period_us;
        if(!g1&&!a1)m->next_odr_us=0;
        break;}
    case SIGNAL_PATH_RESET: if(v&0x02){m->used=0;m->reg[INT_STATUS]&=~0x02;}return;
    case WHO_AM_I: icm_violation(m,"write to read-only WHO_AM_I");return;
    }
    m->reg[a]=v;
}
void icm_transfer(icm_model_t *m,const uint8_t *tx,uint8_t *rx,size_t bytes){
    memset(rx,m->absent?0xFF:0x00,bytes);
    if(m->absent||!bytes)return;
    if(m->now_us<m->reset_until_us){icm_violation(m,"SPI access within 1 ms of power-up or soft reset");return;}
    uint8_t a=tx[0]&0x7F;bool read=tx[0]&0x80;
    if(m->reg[REG_BANK_SEL]!=0&&a!=REG_BANK_SEL)icm_violation(m,"access while a non-zero register bank is selected");
    for(size_t i=1;i<bytes;i++){
        if(read){
            if(a==FIFO_DATA){
                if(m->used){rx[i]=m->fifo[0];memmove(m->fifo,m->fifo+1,--m->used);
                    if(m->used%16==0){m->popped_times[m->popped++]=m->fifo_times[0];memmove(m->fifo_times,m->fifo_times+1,sizeof(double)*(m->used/16));}}
                else rx[i]=0x80; /* empty-FIFO header */
            } else rx[i]=read_reg(m,(uint8_t)(a+i-1));
        } else write_reg(m,(uint8_t)(a+i-1),tx[i]);
    }
    if(read&&a==FIFO_DATA&&((bytes-1)%16))icm_violation(m,"partial FIFO packet read with FIFO_RESUME_PARTIAL_RD=0");
}
