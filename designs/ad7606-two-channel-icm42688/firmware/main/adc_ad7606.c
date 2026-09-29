#include "board.h"
#if AFO_AD7606
#include "sensors.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "driver/gptimer.h"
#include "esp_timer.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdatomic.h>
#define TRY(x) do { esp_err_t e=(x); if(e!=ESP_OK)return e; } while(0)
static spi_device_handle_t adc;
static gptimer_handle_t timer;
static atomic_bool pending,stream_fault;
static uint64_t trigger_stamp;
static portMUX_TYPE stamp_lock=portMUX_INITIALIZER_UNLOCKED;
static bool tick(gptimer_handle_t t,const gptimer_alarm_event_data_t *event,void *ctx){
    (void)t;(void)event;(void)ctx;
    if(atomic_load(&stream_fault))return false;
    // Do not overwrite an unread conversion. Stop rather than relabel old data.
    if(atomic_load(&pending)||gpio_get_level(ADC_DRDY)){atomic_store(&stream_fault,true);return false;}
    atomic_store(&pending,true);
    portENTER_CRITICAL_ISR(&stamp_lock);trigger_stamp=esp_timer_get_time();
    gpio_set_level(ADC_CONVST,1);portEXIT_CRITICAL_ISR(&stamp_lock);
    esp_rom_delay_us(1);gpio_set_level(ADC_CONVST,0);return false;
}
uint64_t adc_sample_timestamp(void){portENTER_CRITICAL_ISR(&stamp_lock);uint64_t x=trigger_stamp;portEXIT_CRITICAL_ISR(&stamp_lock);return x;}
esp_err_t adc_configure(void){
    gpio_config_t o={.pin_bit_mask=(1ULL<<ADC_RESET)|(1ULL<<ADC_CONVST),.mode=GPIO_MODE_OUTPUT};TRY(gpio_config(&o));
    gpio_set_level(ADC_CONVST,0);gpio_set_level(ADC_RESET,1);esp_rom_delay_us(2);gpio_set_level(ADC_RESET,0);vTaskDelay(pdMS_TO_TICKS(10));
    atomic_store(&pending,false);atomic_store(&stream_fault,false);return ESP_OK;
}
esp_err_t adc_bus_init(void){
    spi_bus_config_t b={.mosi_io_num=-1,.miso_io_num=ADC_MISO,.sclk_io_num=ADC_SCK,.quadwp_io_num=-1,.quadhd_io_num=-1,.max_transfer_sz=16};
    TRY(spi_bus_initialize(SPI2_HOST,&b,SPI_DMA_DISABLED));
    // AD7606 updates DOUT on rising SCLK; sample on falling edge, idle high (mode 2).
    spi_device_interface_config_t d={.clock_speed_hz=8000000,.mode=2,.spics_io_num=ADC_CS,.queue_size=1};
    TRY(spi_bus_add_device(SPI2_HOST,&d,&adc));TRY(adc_configure());
    gptimer_config_t c={.clk_src=GPTIMER_CLK_SRC_DEFAULT,.direction=GPTIMER_COUNT_UP,.resolution_hz=1000000};TRY(gptimer_new_timer(&c,&timer));
    gptimer_event_callbacks_t cb={.on_alarm=tick};TRY(gptimer_register_event_callbacks(timer,&cb,NULL));
    gptimer_alarm_config_t a={.alarm_count=125,.reload_count=0,.flags.auto_reload_on_alarm=true};TRY(gptimer_set_alarm_action(timer,&a));return gptimer_enable(timer);
}
esp_err_t adc_stream_start(void){atomic_store(&pending,false);atomic_store(&stream_fault,false);TRY(gptimer_set_raw_count(timer,0));return gptimer_start(timer);}
void adc_stream_stop(void){if(timer)gptimer_stop(timer);gpio_set_level(ADC_CONVST,0);}
esp_err_t emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc){
    if(atomic_load(&stream_fault)||!atomic_load(&pending)||gpio_get_level(ADC_DRDY))return ESP_ERR_INVALID_STATE;
    uint8_t rx[16]={0};spi_transaction_t t={.length=128,.rx_buffer=rx};TRY(spi_device_polling_transmit(adc,&t));
    for(unsigned i=0;i<4;i++){uint16_t u=((uint16_t)rx[2*i]<<8)|rx[2*i+1];codes[i]=i<EMG_CHANNEL_COUNT?(u&0x8000?(int32_t)u-65536:(int32_t)u):0;}
    *status=0;*crc=0; // Original AD7606 has no sensor-frame CRC. Container CRC is separate.
    atomic_store(&pending,false);return atomic_load(&stream_fault)?ESP_ERR_TIMEOUT:ESP_OK;
}
#endif
