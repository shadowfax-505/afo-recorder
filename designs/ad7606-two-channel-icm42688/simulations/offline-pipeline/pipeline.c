// Local logical co-simulation. Executes the production peripheral drivers,
// timestamp helper and binary serializer, with explicit ideal peripheral APIs.
// Not ESP32 execution, a real scheduler, SDMMC, radio or analog measurements.
#include "mock_idf.h"
#include "../../firmware/main/board.h"
#include "../../firmware/main/sensors.h"
#include "../../firmware/main/format.h"
#include "../../firmware/main/imu_timing.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static int64_t now_us,busy_until;
static int levels[64],battery_input=1900,mode_fault,ignore_conversion;
static unsigned active_seq,notifications,wrong_register,imu_transfer_us;
static bool recording_model;
static int16_t stimulus[8000][2];
static gptimer_event_callbacks_t callback;
typedef struct {uint8_t regs[128],fifo[2048];unsigned used,generated;uint16_t ticks;
    double next_us,period_us;} imu_model_t;
static imu_model_t devices[2];
static void advance_to(int64_t target){
    assert(target>=now_us);
    for(unsigned id=0;id<2;id++){
        imu_model_t *m=&devices[id];
        if(!m->next_us){m->period_us=5000*(1+(id?-110:70)*1e-6);m->next_us=target+m->period_us;}
        while(m->next_us<=target){
            if(m->regs[0x16]==0x40&&m->regs[0x4e]==0x0f){
                uint8_t packet[16]={0x68,0,0,0,0,8,0};m->ticks+=5000;m->generated++;
                packet[2]=id+1;packet[14]=m->ticks>>8;packet[15]=m->ticks;
                if(m->used+16<=2048){memcpy(m->fifo+m->used,packet,16);m->used+=16;}
                else m->regs[0x2d]|=2;
            }
            m->next_us+=m->period_us;
        }
    }
    now_us=target;
}
esp_err_t gpio_config(const gpio_config_t *c){(void)c;return ESP_OK;}
int gpio_set_level(int p,int v){if(p==ADC_CONVST&&v&&!ignore_conversion)busy_until=now_us+4;levels[p]=v;return 0;}
int gpio_get_level(int p){return p==ADC_DRDY?now_us<busy_until:levels[p];}
int64_t esp_timer_get_time(void){return now_us;}
void esp_rom_delay_us(unsigned us){advance_to(now_us+us);}
void vTaskDelay(unsigned ms){advance_to(now_us+ms*1000);}
esp_err_t spi_bus_initialize(int host,const spi_bus_config_t *b,int dma){
    if(host==SPI2_HOST)assert(dma==SPI_DMA_DISABLED&&b->miso_io_num==13&&b->sclk_io_num==12&&b->mosi_io_num==-1);
    else assert(host==SPI3_HOST&&dma==SPI_DMA_CH_AUTO&&b->mosi_io_num==4&&b->miso_io_num==5&&b->sclk_io_num==6&&b->max_transfer_sz==2049);
    return ESP_OK;
}
esp_err_t spi_bus_add_device(int host,const spi_device_interface_config_t *d,spi_device_handle_t *h){
    if(host==SPI2_HOST){assert(d->mode==2&&d->clock_speed_hz==8000000&&d->spics_io_num==10);*h=(void*)1;}
    else {assert(d->mode==0&&d->clock_speed_hz==1000000);assert(d->spics_io_num==7||d->spics_io_num==15);*h=(void*)(uintptr_t)(d->spics_io_num==7?2:3);}
    return ESP_OK;
}
esp_err_t spi_device_polling_transmit(spi_device_handle_t handle,spi_transaction_t *t){
    if(handle==(void*)1){
        assert(t->length==128);uint8_t *rx=t->rx_buffer;
        if(!levels[ADC_RESET])assert(now_us>=busy_until);
        for(unsigned i=0;i<8;i++){
            uint16_t code=mode_fault?0xffff:(i<2?(uint16_t)stimulus[active_seq%8000][i]:0);
            rx[2*i]=code>>8;rx[2*i+1]=code;
        }
        advance_to(now_us+16);return ESP_OK;
    }
    unsigned id=(unsigned)(uintptr_t)handle-2;assert(id<2);imu_model_t *m=&devices[id];
    const uint8_t *tx=t->flags&SPI_TRANS_USE_TXDATA?t->tx_data:t->tx_buffer;
    unsigned reg=tx[0]&127,n=t->length/8;
    if(tx[0]&128){
        uint8_t *rx=t->rx_buffer;assert(rx);rx[0]=0;
        if(reg==0x30){assert(n-1<=m->used);memcpy(rx+1,m->fifo,n-1);memmove(m->fifo,m->fifo+n-1,m->used-(n-1));m->used-=n-1;}
        else for(unsigned i=1;i<n;i++){
            unsigned r=(reg+i-1)&127;
            rx[i]=r==0x2e?m->used>>8:r==0x2f?m->used:m->regs[r];
            if(wrong_register&&r==0x50)rx[i]^=1;
            if(r==0x2d)m->regs[r]=0;
        }
    } else {
        assert(n==2);
        if(reg==0x11&&(tx[1]&1)){memset(m->regs,0,128);m->regs[0x75]=0x47;m->used=0;}
        else {m->regs[reg]=tx[1];if(reg==0x4b&&(tx[1]&2))m->used=0;}
    }
    imu_transfer_us+=n*8;
    if(!recording_model)advance_to(now_us+n*8);
    return ESP_OK;
}
esp_err_t gptimer_new_timer(const gptimer_config_t *c,gptimer_handle_t *h){assert(c->resolution_hz==1000000);*h=(void*)1;return ESP_OK;}
esp_err_t gptimer_register_event_callbacks(gptimer_handle_t h,const gptimer_event_callbacks_t *c,void *p){(void)h;(void)p;callback=*c;return ESP_OK;}
esp_err_t gptimer_set_alarm_action(gptimer_handle_t h,const gptimer_alarm_config_t *a){(void)h;assert(a->alarm_count==125&&a->flags.auto_reload_on_alarm);return ESP_OK;}
esp_err_t gptimer_enable(gptimer_handle_t h){(void)h;return ESP_OK;}
esp_err_t gptimer_set_raw_count(gptimer_handle_t h,uint64_t c){(void)h;assert(c==0);return ESP_OK;}
esp_err_t gptimer_start(gptimer_handle_t h){(void)h;return ESP_OK;}
esp_err_t gptimer_stop(gptimer_handle_t h){(void)h;return ESP_OK;}
esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *c,adc_oneshot_unit_handle_t *h){assert(c->unit_id==1);*h=(void*)1;return ESP_OK;}
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t h,int ch,const adc_oneshot_chan_cfg_t *c){assert(h&&ch==0&&c->atten==12);return ESP_OK;}
esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *c,adc_cali_handle_t *h){assert(c->unit_id==1&&c->chan==0);*h=(void*)1;return ESP_OK;}
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t h,int ch,int *raw){assert(h&&ch==0);*raw=battery_input;return ESP_OK;}
esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t h,int raw,int *mv){assert(h);*mv=raw;return ESP_OK;}
static bool triggered(void *arg){(void)arg;notifications++;return true;}
static void save(FILE *f,const afo_record_t *r){assert(fwrite(r,1,sizeof(*r),f)==sizeof(*r));}
int main(int argc,char **argv){
    assert(argc==4||argc==5);unsigned sample_count=16000;
    if(argc==5){char *end;unsigned long parsed=strtoul(argv[4],&end,10);assert(!*end&&parsed>=16000&&parsed<=28800000);sample_count=(unsigned)parsed;}
    FILE *input=fopen(argv[1],"r");assert(input);char row[256];assert(fgets(row,sizeof(row),input));
    for(unsigned i=0;i<8000;i++){
        unsigned index;double time,a,b;int c,d;
        assert(fgets(row,sizeof(row),input));assert(sscanf(row,"%u,%lf,%lf,%lf,%d,%d",&index,&time,&a,&b,&c,&d)==6&&index==i);
        stimulus[i][0]=c;stimulus[i][1]=d;
    }
    fclose(input);FILE *meta=fopen(argv[2],"r");assert(meta);char json[4077];size_t n=fread(json,1,4076,meta);json[n]=0;fclose(meta);
    afo_format_init();assert(adc_bus_init()==ESP_OK&&imu_bus_init(2)==ESP_OK&&battery_init()==ESP_OK);
    assert(battery_mv()==3800);battery_input=1600;assert(battery_mv()==3200);battery_input=1900;
    puts("PASS configured converter, independent IMUs and calibrated-voltage API path");
    wrong_register=1;assert(imu_bus_init(2)==ESP_ERR_INVALID_RESPONSE);wrong_register=0;
    assert(imu_bus_init(2)==ESP_OK);puts("PASS IMU configuration readback rejects mismatch");
    uint8_t bytes[2048];size_t packets;bool over;
    devices[0].regs[0x2d]=2;assert(imu_fifo(0,bytes,sizeof(bytes),&packets,&over)==ESP_OK&&over);
    devices[0].used=2048;assert(imu_fifo(0,bytes,sizeof(bytes),&packets,&over)==ESP_OK&&over&&!devices[0].used);
    devices[0].used=16;assert(imu_fifo(0,bytes,8,&packets,&over)==ESP_ERR_INVALID_SIZE);devices[0].used=0;
    puts("PASS overflow status, full FIFO and insufficient receive capacity");
    assert(imu_start(0)==ESP_OK&&imu_start(1)==ESP_OK);
    FILE *output=fopen(argv[3],"wb");assert(output);uint8_t header[AFO_HEADER_BYTES];assert(!afo_header(header,json));assert(fwrite(header,1,sizeof(header),output)==sizeof(header));
    adc_set_trigger_callback(triggered,NULL);assert(adc_stream_start()==ESP_OK);recording_model=true;
    unsigned counts[2]={0},rollovers[2]={0};uint16_t last_ticks[2]={0};uint64_t last_estimates[2]={0};
    unsigned before_capture[2]={devices[0].generated,devices[1].generated};
    imu_clock_t clocks[2]={0};int64_t origin=now_us+125;
    for(active_seq=0;active_seq<sample_count;active_seq++){
        advance_to(origin+(uint64_t)active_seq*125);assert(callback.on_alarm(NULL,NULL,NULL));
        uint64_t stamp=adc_sample_timestamp();emg_payload_t payload={.elapsed_slots=1,.active_mask=3};
        payload.read_start_us=now_us;int32_t raw[4];uint16_t status,crc;
        assert(emg_frame(raw,&status,&crc)==ESP_OK);
        memcpy(payload.codes,raw,sizeof(raw));payload.adc_status=status;payload.adc_crc=crc;
        payload.read_duration_us=now_us-payload.read_start_us;
        assert(payload.codes[0]==stimulus[active_seq%8000][0]&&payload.codes[1]==stimulus[active_seq%8000][1]&&!payload.codes[2]&&!payload.codes[3]);
        afo_record_t record;afo_record_init(&record,7,0,active_seq+1,stamp,&payload,sizeof(payload));save(output,&record);
        if(active_seq%40==20)for(unsigned id=0;id<2;id++){
            uint64_t start=now_us;imu_transfer_us=0;assert(imu_fifo(id,bytes,sizeof(bytes),&packets,&over)==ESP_OK&&!over);
            uint64_t end=start+imu_transfer_us;unsigned lag=(packets?packets-1:0)*5000;
            for(unsigned k=0;k<packets;k++){
                uint8_t *p=bytes+k*16;uint16_t ticks=((uint16_t)p[14]<<8)|p[15];uint64_t estimate;bool gap;
                assert(imu_clock_step(&clocks[id],ticks,start-lag+k*5000,start,&estimate,&gap)&&!gap);
                assert(p[1]==0&&p[2]==id+1&&p[3]==0&&p[4]==0&&p[5]==8&&p[6]==0);
                if(counts[id]){assert((uint16_t)(ticks-last_ticks[id])==5000&&estimate>last_estimates[id]);if(ticks<last_ticks[id])rollovers[id]++;}
                last_ticks[id]=ticks;last_estimates[id]=estimate;
                imu_payload_t body={.read_start_us=start,.read_end_us=end,.irq_anchor_us=start};memcpy(body.fifo_packet,p,16);
                afo_record_init(&record,id?REC_SHANK:REC_FOOT,FLAG_TIMING_UNCERTAIN,++counts[id],estimate,&body,sizeof(body));save(output,&record);
            }
            // Separate IMU-bus transfer windows are recorded as modeled durations.
            // The ordered host calls do not simulate RTOS CPU/interrupt contention.
        }
    }
    adc_stream_stop();unsigned pending[2]={devices[0].used/16,devices[1].used/16};
    assert(counts[0]+pending[0]==devices[0].generated&&counts[1]+pending[1]==devices[1].generated);
    assert(imu_stop(0)==ESP_OK&&imu_stop(1)==ESP_OK&&notifications==sample_count);
    status_payload_t status={.emg_records=sample_count,.foot_records=counts[0],.shank_records=counts[1],.battery_mv=3800};
    afo_record_t last;afo_record_init(&last,REC_END,0,1,now_us+100,&status,sizeof(status));save(output,&last);assert(!fclose(output));
    printf("PASS filtered input -> real C drivers -> timestamp helper -> serializer; emg=%u,foot=%u,shank=%u\n",sample_count,counts[0],counts[1]);
    printf("MODEL {\"sample_count\":%u,\"duration_us\":%u,\"foot\":{\"saved\":%u,\"generated\":%u,\"generated_before_capture\":%u,\"pending_at_stop\":%u,\"counter_rollovers\":%u},\"shank\":{\"saved\":%u,\"generated\":%u,\"generated_before_capture\":%u,\"pending_at_stop\":%u,\"counter_rollovers\":%u}}\n",
        sample_count,sample_count*125,counts[0],devices[0].generated,before_capture[0],pending[0],rollovers[0],counts[1],devices[1].generated,before_capture[1],pending[1],rollovers[1]);
    mode_fault=1;advance_to(now_us+125);callback.on_alarm(NULL,NULL,NULL);int32_t codes[4];uint16_t flags,crc;
    assert(emg_frame(codes,&flags,&crc)==ESP_OK&&codes[0]==-1&&codes[1]==-1);
    puts("PASS wrong serial mode can produce plausible -1 codes; known-input qualification is essential");
    mode_fault=0;ignore_conversion=1;advance_to(now_us+125);callback.on_alarm(NULL,NULL,NULL);
    assert(emg_frame(codes,&flags,&crc)==ESP_ERR_TIMEOUT);
    puts("PASS ignored conversion trigger or BUSY stuck low is rejected, not saved as a stale valid frame");
    return 0;
}
