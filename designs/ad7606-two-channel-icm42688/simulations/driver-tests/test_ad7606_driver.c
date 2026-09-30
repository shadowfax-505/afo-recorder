// Execute the unmodified production driver with deterministic peripheral stubs.
// This checks C logic, not ESP32 execution, concurrency or electrical timing.
#include "mock_idf.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../firmware/main/adc_ad7606.c"
static int levels[64],pulses,reads;
static int64_t clock_us;
static int64_t busy_until;
static unsigned notifications;
static unsigned accepted_conversions;
static bool busy_disconnected,ignore_conversion;
static bool late_during_read;
static esp_err_t read_error,bus_error;
static int16_t words[8];
static gptimer_event_callbacks_t callback;
esp_err_t gpio_config(const gpio_config_t *c){(void)c;return ESP_OK;}
int gpio_get_level(int pin){
 if(pin==ADC_DRDY){
  if(busy_disconnected)return 0;
  if(busy_until&&clock_us>=busy_until)levels[pin]=0;
 }
 return levels[pin];
}
int gpio_set_level(int pin,int v){
 if(pin==ADC_CONVST&&v&&!levels[pin]){
  pulses++;
  // The default converter accepts CONVST immediately and asserts BUSY for
  // 4 us. Disconnected BUSY and an ignored CONVST are independent failures.
  if(!ignore_conversion){accepted_conversions++;levels[ADC_DRDY]=1;busy_until=clock_us+4;}
 }
 levels[pin]=v;return 0;
}
int64_t esp_timer_get_time(void){return clock_us;}
void esp_rom_delay_us(unsigned us){clock_us+=us;}
void vTaskDelay(unsigned ms){clock_us+=ms*1000;}
esp_err_t spi_bus_initialize(int host,const spi_bus_config_t *b,int dma){
 assert(host==SPI2_HOST&&dma==SPI_DMA_DISABLED);
 assert(b->miso_io_num==13&&b->sclk_io_num==12&&b->mosi_io_num==-1&&b->max_transfer_sz==16);
 return bus_error;
}
esp_err_t spi_bus_add_device(int host,const spi_device_interface_config_t *d,spi_device_handle_t *handle){
 assert(host==SPI2_HOST&&d->mode==2&&d->clock_speed_hz==8000000&&d->spics_io_num==10);
 *handle=(void*)1;return ESP_OK;
}
esp_err_t spi_device_polling_transmit(spi_device_handle_t handle,spi_transaction_t *t){
 assert(handle&&t->length==128);reads++;
 if(levels[ADC_RESET])assert(!levels[ADC_CONVST]&&pulses==0);
 else assert(!gpio_get_level(ADC_DRDY)); // Never clock data before conversion completion.
 if(read_error)return read_error;
 uint8_t *rx=t->rx_buffer;
 for(unsigned i=0;i<8;i++){uint16_t w=(uint16_t)words[i];rx[i*2]=w>>8;rx[i*2+1]=w;}
 clock_us+=16; // Nominal 128 serial clocks at 8 MHz, excluding API overhead.
 if(late_during_read){clock_us+=125;callback.on_alarm(timer,NULL,NULL);}
 return ESP_OK;
}
esp_err_t gptimer_new_timer(const gptimer_config_t *c,gptimer_handle_t *h){assert(c->resolution_hz==1000000);*h=(void*)1;return ESP_OK;}
esp_err_t gptimer_register_event_callbacks(gptimer_handle_t h,const gptimer_event_callbacks_t *c,void *u){(void)h;(void)u;callback=*c;return ESP_OK;}
esp_err_t gptimer_set_alarm_action(gptimer_handle_t h,const gptimer_alarm_config_t *c){(void)h;assert(c->alarm_count==125&&c->reload_count==0&&c->flags.auto_reload_on_alarm);return ESP_OK;}
esp_err_t gptimer_enable(gptimer_handle_t h){(void)h;return ESP_OK;}
esp_err_t gptimer_set_raw_count(gptimer_handle_t h,uint64_t c){(void)h;assert(c==0);return ESP_OK;}
esp_err_t gptimer_start(gptimer_handle_t h){(void)h;return ESP_OK;}
esp_err_t gptimer_stop(gptimer_handle_t h){(void)h;return ESP_OK;}
static void reset_case(void){
 memset(levels,0,sizeof(levels));pulses=reads=0;clock_us=busy_until=0;notifications=accepted_conversions=0;
 busy_disconnected=ignore_conversion=false;
 adc_set_trigger_callback(NULL,NULL);
 late_during_read=false;read_error=bus_error=ESP_OK;
 assert(adc_bus_init()==ESP_OK);assert(reads==1&&pulses==0&&!levels[ADC_RESET]);
 reads=0;assert(adc_stream_start()==ESP_OK);
}
static void trigger(void){clock_us+=125;callback.on_alarm(timer,NULL,NULL);}
static bool notified(void *context){assert(context==(void*)42);notifications++;return true;}
int main(void){
 int32_t codes[4];uint16_t status,crc;
 reset_case();puts("PASS SPI mode primed during RESET before any measured conversion");
 reset_case();assert(emg_frame(codes,&status,&crc)==ESP_ERR_INVALID_STATE&&reads==0);
 puts("PASS no read before conversion");
 words[0]=6554;words[1]=-1234;words[2]=32767;words[3]=-32768;
 trigger();uint64_t stamp=adc_sample_timestamp();assert(pulses==1&&!levels[ADC_CONVST]);
 assert(emg_frame(codes,&status,&crc)==ESP_OK);
 assert(codes[0]==6554&&codes[1]==-1234&&codes[2]==0&&codes[3]==0&&status==0&&crc==0);
 assert(adc_sample_timestamp()==stamp);assert(emg_frame(codes,&status,&crc)==ESP_ERR_INVALID_STATE);
 puts("PASS 128-clock read, signed order, disabled channels and trigger timestamp");
 reset_case();trigger();stamp=adc_sample_timestamp();
 assert(levels[ADC_DRDY]&&(uint64_t)clock_us==stamp+1&&accepted_conversions==1&&reads==0);
 assert(emg_frame(codes,&status,&crc)==ESP_OK&&(uint64_t)clock_us==stamp+20);
 assert(reads==1&&!gpio_get_level(ADC_DRDY));
 puts("PASS ordinary BUSY assertion is confirmed; complete conversion precedes the 16us serial read");
 reset_case();adc_set_trigger_callback(notified,(void*)42);busy_disconnected=true;
 trigger();assert(pulses==1&&accepted_conversions==1&&notifications==1&&atomic_load(&stream_fault));
 assert(emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT&&reads==0);
 trigger();trigger();assert(pulses==1&&notifications==1);
 puts("PASS disconnected or stuck-low BUSY faults before plausible stale codes can be read");
 reset_case();adc_set_trigger_callback(notified,(void*)42);ignore_conversion=true;
 trigger();assert(pulses==1&&accepted_conversions==0&&notifications==1&&atomic_load(&stream_fault));
 assert(emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT&&reads==0);
 trigger();assert(pulses==1&&accepted_conversions==0);
 puts("PASS ignored CONVST is detected and later conversion pulses remain inhibited");
 ignore_conversion=false;assert(adc_stream_start()==ESP_OK);trigger();
 assert(pulses==2&&accepted_conversions==1&&notifications==2&&!atomic_load(&stream_fault));
 assert(emg_frame(codes,&status,&crc)==ESP_OK&&reads==1);
 puts("PASS intentional restart after a missing BUSY assertion requires a fresh accepted conversion");
 reset_case();levels[ADC_DRDY]=1;trigger();assert(pulses==0&&atomic_load(&stream_fault));
 levels[ADC_DRDY]=0;trigger();assert(pulses==0);puts("PASS preexisting BUSY inhibits trigger and latches fault");
 reset_case();trigger();stamp=adc_sample_timestamp();trigger();trigger();
 assert(pulses==1&&adc_sample_timestamp()==stamp&&emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT);
 puts("PASS unread conversion is never overwritten or relabeled");
 reset_case();trigger();levels[ADC_DRDY]=1;busy_until=0;
 assert(emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT&&reads==0);
 trigger();levels[ADC_DRDY]=0;trigger();assert(pulses==1);
 puts("PASS stuck BUSY blocks reads and further conversions");
 reset_case();adc_set_trigger_callback(notified,(void*)42);
 clock_us+=125;assert(callback.on_alarm(timer,NULL,NULL));assert(notifications==1);
 levels[ADC_DRDY]=1;busy_until=clock_us+4;
 assert(emg_frame(codes,&status,&crc)==ESP_OK&&!levels[ADC_DRDY]);
 trigger();trigger();assert(notifications==2&&atomic_load(&stream_fault));
 puts("PASS timer notification occurs once per accepted trigger; BUSY completion precedes read");
 reset_case();trigger();levels[ADC_DRDY]=1;busy_until=0;int64_t before=clock_us;
 assert(emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT&&clock_us-before==80&&reads==0);
 puts("PASS 80us BUSY timeout prevents reading incomplete conversion");
 reset_case();trigger();late_during_read=true;
 assert(emg_frame(codes,&status,&crc)==ESP_ERR_TIMEOUT);trigger();assert(pulses==1);
 puts("PASS late SPI completion returns error and stops subsequent triggers");
 reset_case();trigger();read_error=ESP_FAIL;
 assert(emg_frame(codes,&status,&crc)==ESP_FAIL);trigger();assert(atomic_load(&stream_fault));
 puts("PASS SPI error propagates and unread frame faults next deadline");
 read_error=ESP_OK;adc_stream_stop();assert(adc_stream_start()==ESP_OK);trigger();
 assert(emg_frame(codes,&status,&crc)==ESP_OK&&pulses==2);
 puts("PASS explicit restart clears latched fault");
 bus_error=ESP_FAIL;assert(adc_bus_init()==ESP_FAIL);puts("PASS bus initialization error propagates");
 return 0;
}
