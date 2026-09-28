#include "board.h"
#if !AFO_AD7606
#include "sensors.h"
#include "ads_crc.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#define TRY(x) do { esp_err_t e=(x); if(e!=ESP_OK)return e; } while(0)
static spi_device_handle_t adc;
esp_err_t adc_bus_init(void) {
    spi_bus_config_t ab={.mosi_io_num=ADC_MOSI,.miso_io_num=ADC_MISO,
        .sclk_io_num=ADC_SCK,.quadwp_io_num=-1,.quadhd_io_num=-1,.max_transfer_sz=32};
    TRY(spi_bus_initialize(SPI2_HOST,&ab,SPI_DMA_DISABLED));
    spi_device_interface_config_t ac={.clock_speed_hz=8000000,.mode=1,
        .spics_io_num=ADC_CS,.queue_size=1};
    TRY(spi_bus_add_device(SPI2_HOST,&ac,&adc));
    TRY(adc_configure());
    return ESP_OK;
}
/* ADS131M04 SBAS890D: six 24-bit words, command/status + four ADC + CRC.
 * CRC-CCITT seed FFFF, non-reflected, includes zero padding in preceding words.
 * Output CRC is mandatory. Input CRC remains disabled; every setup register is read back.
 */
static esp_err_t adc_exchange(uint16_t command,uint16_t value,uint8_t rx[18]) {
    uint8_t tx[18]={command>>8,command&255,0,value>>8,value&255,0};
    spi_transaction_t t={.length=144,.tx_buffer=tx,.rx_buffer=rx};
    TRY(spi_device_polling_transmit(adc,&t));
    return ads_crc16(rx,15)==((rx[15]<<8)|rx[16]) ? ESP_OK : ESP_ERR_INVALID_CRC;
}
static esp_err_t adc_reg_read(uint8_t reg,uint16_t *value) {
    uint8_t rx[18];TRY(adc_exchange(0xa000|((uint16_t)reg<<7),0,rx));
    TRY(adc_exchange(0,0,rx));*value=(rx[0]<<8)|rx[1];return ESP_OK;
}
static esp_err_t adc_reg_write(uint8_t reg,uint16_t value) {
    uint8_t rx[18];uint16_t got;TRY(adc_exchange(0x6000|((uint16_t)reg<<7),value,rx));
    TRY(adc_exchange(0,0,rx));
    if(((rx[0]<<8)|rx[1])!=(0x4000|((uint16_t)reg<<7)))return ESP_ERR_INVALID_RESPONSE;
    TRY(adc_reg_read(reg,&got));return got==value?ESP_OK:ESP_ERR_INVALID_RESPONSE;
}
esp_err_t adc_configure(void) {
    gpio_config_t cfg={.pin_bit_mask=1ULL<<ADC_RESET,.mode=GPIO_MODE_OUTPUT};
    TRY(gpio_config(&cfg));gpio_set_level(ADC_RESET,0);vTaskDelay(pdMS_TO_TICKS(2));
    gpio_set_level(ADC_RESET,1);vTaskDelay(pdMS_TO_TICKS(10));
    uint16_t id;TRY(adc_reg_read(0,&id));if((id&0xff00)!=0x2400)return ESP_ERR_NOT_FOUND;
    TRY(adc_reg_write(2,ADS_MODE_REG));
    TRY(adc_reg_write(3,ADS_CLOCK_REG));
    TRY(adc_reg_write(4,0)); /* All channel PGA gains=1. */
    vTaskDelay(pdMS_TO_TICKS(10));uint8_t discard[18];
    TRY(adc_exchange(0,0,discard));TRY(adc_exchange(0,0,discard));return ESP_OK;
}
esp_err_t emg_frame(int32_t codes[4],uint16_t *status,uint16_t *crc) {
    uint8_t rx[18];TRY(adc_exchange(0,0,rx));
    int result=ads_decode24(rx,codes,status,crc);
    if(result)return result==1?ESP_ERR_INVALID_CRC:ESP_ERR_INVALID_RESPONSE;
    unsigned mask=(1u<<EMG_CHANNEL_COUNT)-1;
    if((*status&mask)!=mask)return ESP_ERR_INVALID_RESPONSE;
    for(unsigned i=EMG_CHANNEL_COUNT;i<4;i++)codes[i]=0;
    return ESP_OK;
}

esp_err_t adc_stream_start(void){return ESP_OK;}
void adc_stream_stop(void){}
uint64_t adc_sample_timestamp(void){return esp_timer_get_time();}
#endif
