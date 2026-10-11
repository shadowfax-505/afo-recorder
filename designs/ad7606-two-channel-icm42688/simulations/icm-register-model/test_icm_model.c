/* Drive the production sensors.c and imu_timing.h through two ICM-42688-P
 * models on one SPI bus, polling like the firmware IMU task. */
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mock_idf.h"
#include "board.h"
#include "sensors.h"
#include "imu_timing.h"
#include "icm42688_model.h"
static double now_us;static icm_model_t devs[2];
static struct {int cs,mode,clock;} handles[4];static int nhandles;static spi_bus_config_t bus;
static void advance(double us){now_us+=us;icm_advance(&devs[0],now_us);icm_advance(&devs[1],now_us);}
int64_t esp_timer_get_time(void){return (int64_t)now_us;}
void esp_rom_delay_us(unsigned us){advance(us);}
void vTaskDelay(unsigned ticks){advance(ticks*1000.0);}
esp_err_t gpio_config(const gpio_config_t *c){(void)c;return ESP_OK;}
int gpio_set_level(int p,int l){(void)p;(void)l;return 0;}
int gpio_get_level(int p){(void)p;return 0;}
esp_err_t spi_bus_initialize(int host,const spi_bus_config_t *c,int dma){(void)dma;
    if(host==SPI3_HOST){bus=*c;}return ESP_OK;}
esp_err_t spi_bus_add_device(int host,const spi_device_interface_config_t *c,spi_device_handle_t *h){
    (void)host;handles[nhandles]=(typeof(handles[0])){c->spics_io_num,c->mode,c->clock_speed_hz};*h=&handles[nhandles++];return ESP_OK;}
esp_err_t spi_device_polling_transmit(spi_device_handle_t h,spi_transaction_t *t){
    typeof(handles[0]) *d=h;size_t bytes=t->length/8;assert(t->length%8==0);
    if(d->mode!=0&&d->mode!=3){fprintf(stderr,"SPI mode %d not supported by ICM-42688 default\n",d->mode);abort();}
    if(d->clock>24000000){fprintf(stderr,"SPI clock above 24 MHz\n");abort();}
    icm_model_t *m=d->cs==FOOT_CS?&devs[0]:d->cs==SHANK_CS?&devs[1]:NULL;assert(m);
    const uint8_t *tx=(t->flags&SPI_TRANS_USE_TXDATA)?t->tx_data:t->tx_buffer;
    uint8_t rx[4096];icm_transfer(m,tx,rx,bytes);
    if(t->rx_buffer)memcpy(t->rx_buffer,rx,bytes);
    advance(bytes*8.0*1e6/d->clock+3);return ESP_OK;
}
/* ADC and battery pieces of sensors.c are not exercised here. */
esp_err_t adc_bus_init(void){return ESP_OK;}
esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *a,adc_oneshot_unit_handle_t *b){(void)a;(void)b;return ESP_OK;}
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t a,int b,const adc_oneshot_chan_cfg_t *c){(void)a;(void)b;(void)c;return ESP_OK;}
esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *a,adc_cali_handle_t *b){(void)a;(void)b;return ESP_OK;}
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t a,int b,int *c){(void)a;(void)b;*c=0;return ESP_OK;}
esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t a,int b,int *c){(void)a;(void)b;*c=0;return ESP_OK;}

static double last_irq_before(const icm_model_t *m,double t,size_t *count){
    size_t n=0;while(n<m->irq_count&&m->irq_times[n]<=t)n++;*count=n;return n?m->irq_times[n-1]:0;}
typedef struct {size_t packets,invalid,header_errors,gaps;double max_err_us,last_err_us,first_err_us;bool overflow;esp_err_t error;} result_t;
/* Same steps as main.c imu_task for one sensor, without the recorder queue. */
static void run(double seconds,unsigned stall_ms,result_t res[2]){
    imu_clock_t clocks[2]={0};uint8_t data[2048];memset(res,0,2*sizeof(result_t));
    double end=now_us+seconds*1e6,stall_at=now_us+10e6;
    while(now_us<end){
        for(int id=0;id<2;id++){
            size_t before,after;double anchor=last_irq_before(&devs[id],now_us,&before);
            if(!anchor)continue;
            uint64_t t0=(uint64_t)now_us;size_t packets;bool overflow;
            esp_err_t e=imu_fifo(id,data,sizeof data,&packets,&overflow);
            (void)last_irq_before(&devs[id],now_us,&after);
            if(e!=ESP_OK){res[id].error=e;return;}
            if(overflow){res[id].overflow=true;return;}
            uint64_t lag[128]={0};
            for(int k=(int)packets-2;k>=0;k--){uint16_t a=(data[k*16+14]<<8)|data[k*16+15],b=(data[(k+1)*16+14]<<8)|data[(k+1)*16+15];lag[k]=lag[k+1]+(uint16_t)(b-a);}
            for(size_t k=0;k<packets;k++){
                const uint8_t *p=data+16*k;
                if((p[0]&0xfc)!=0x68){res[id].header_errors++;continue;}
                for(int j=1;j<13;j+=2)if(p[j]==0x80&&p[j+1]==0){res[id].invalid++;break;}
                uint16_t ticks=(p[14]<<8)|p[15];uint64_t lag_us=imu_ticks_to_us(lag[k]),estimate;bool gap;
                if(!imu_clock_step(&clocks[id],ticks,(uint64_t)anchor>=lag_us?(uint64_t)anchor-lag_us:0,t0,&estimate,&gap)){res[id].error=-1;return;}
                if(gap)res[id].gaps++;
                double truth=devs[id].popped_times[res[id].packets];
                double err=estimate-truth;if(!res[id].packets)res[id].first_err_us=err;
                if(fabs(err)>res[id].max_err_us)res[id].max_err_us=fabs(err);res[id].last_err_us=err;res[id].packets++;
                int16_t az=(int16_t)((p[5]<<8)|p[6]);
                if(az!=2048&&!(p[5]==0x80&&p[6]==0)){fprintf(stderr,"wrong byte order/axis: az=%d\n",az);abort();}
            }
            (void)after;
        }
        if(stall_ms&&now_us>=stall_at){vTaskDelay(stall_ms);stall_ms=0;}
        vTaskDelay(1);
    }
}
static void setup(double ppm0,double ppm1){
    now_us=0;nhandles=0;icm_init(&devs[0],"foot",ppm0);icm_init(&devs[1],"shank",ppm1);
    advance(300000); /* ESP32 boot before app_main */
}
static int failures;
#define CHECK(c,msg) do{if(!(c)){printf("FAIL %s\n",msg);failures++;}else printf("PASS %s\n",msg);}while(0)
int main(void){
    result_t r[2];
    setup(0,0);
    CHECK(imu_bus_init(2)==ESP_OK,"both sensors identify (WHO_AM_I 0x47) and every configuration write reads back");
    CHECK(bus.mosi_io_num==IMU_MOSI&&bus.miso_io_num==IMU_MISO&&bus.sclk_io_num==IMU_SCK,"SPI3 uses GPIO4 MOSI, GPIO5 MISO, GPIO6 SCLK");
    CHECK(handles[0].cs==FOOT_CS&&handles[1].cs==SHANK_CS&&handles[0].mode==0&&handles[0].clock==1000000,"foot CS GPIO7, shank CS GPIO15, SPI mode 0 at 1 MHz");
    uint8_t want[][2]={{0x4C,0x33},{0x4E,0x00},{0x4F,0x07},{0x50,0x07},{0x51,0x16},{0x52,0x44},{0x53,0x0D},{0x54,0x21},{0x5F,0x0F},{0x14,0x03},{0x64,0x00},{0x65,0x08}};
    bool cfg=true;for(int id=0;id<2;id++)for(size_t i=0;i<sizeof want/2;i++)cfg&=devs[id].reg[want[i][0]]==want[i][1];
    CHECK(cfg,"final register state: I2C off, big-endian, byte count; 2000 dps/16 g at 200 Hz; 2nd-order 40 Hz filters; 1 us-mode timestamp; 16-byte packets; INT1 push-pull active-high pulsed, data-ready only");
    CHECK(imu_start(0)==ESP_OK&&imu_start(1)==ESP_OK,"both sensors start in low-noise mode and stream to FIFO");
    run(60,0,r);
    CHECK(devs[0].violations==0&&devs[1].violations==0,"no datasheet rule violated (1 ms reset wait, 200 us power-on write blackout, reserved bits, valid codes, INT1 setup, whole-packet FIFO reads)");
    for(int id=0;id<2;id++){
        char msg[200];
        snprintf(msg,sizeof msg,"%s: %zu packets in 60 s (expect ~12000), no header error, overflow or invalid sample",id?"shank":"foot",r[id].packets);
        CHECK(r[id].packets>=11990&&r[id].packets<=12010&&!r[id].header_errors&&!r[id].overflow&&!r[id].invalid&&!r[id].error,msg);
        snprintf(msg,sizeof msg,"%s: host-time estimate error max %.1f us (first %.1f, last %.1f) with an exact sensor clock",id?"shank":"foot",r[id].max_err_us,r[id].first_err_us,r[id].last_err_us);
        CHECK(r[id].max_err_us<=10,msg);
    }
    CHECK(imu_stop(0)==ESP_OK&&imu_stop(1)==ESP_OK&&devs[0].violations==0,"stop after the 45 ms gyro minimum on-time");

    /* Datasheet allows +/-1% ODR error in PLL mode. */
    setup(5000,-5000);imu_bus_init(2);imu_start(0);imu_start(1);run(60,0,r);
    printf("INFO sensor clock +0.5%%/-0.5%%: estimate drift after 60 s foot %.0f us, shank %.0f us (estimates follow the sensor clock; correct offline from IRQ anchors)\n",r[0].last_err_us,r[1].last_err_us);
    CHECK(fabs(r[0].last_err_us+300000)<2000&&fabs(r[1].last_err_us-300000)<2000,"0.5% sensor clock error appears as about 300 ms drift per minute, exactly as modeled");

    setup(0,0);devs[1].absent=true;
    CHECK(imu_bus_init(2)==ESP_ERR_NOT_FOUND,"shank with SPI jumpers in I2C position (no MISO response) fails identification");
    setup(0,0);devs[0].stuck_addr=0x52;
    CHECK(imu_bus_init(2)==ESP_ERR_INVALID_RESPONSE,"a register that does not accept writes fails configuration readback");
    setup(0,0);imu_bus_init(2);imu_start(0);imu_start(1);run(12,800,r);
    CHECK(r[0].overflow||r[1].overflow,"an 800 ms polling stall overflows the 2048-byte FIFO and is reported, not silently skipped");
    printf(failures?"RESULT FAIL %d\n":"RESULT PASS\n",failures);
    return failures!=0;
}
