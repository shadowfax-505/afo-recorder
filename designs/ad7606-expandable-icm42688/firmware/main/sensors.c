#include "sensors.h"
#include "ads_crc.h"
#include "board.h"
#include <string.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#define TRY(x) do { esp_err_t e=(x); if(e!=ESP_OK) return e; } while(0)
static spi_device_handle_t imu[2];
static adc_oneshot_unit_handle_t battery_adc;
static adc_cali_handle_t battery_cal;
static esp_err_t reg_write(unsigned id,uint8_t reg,uint8_t value) {
    spi_transaction_t t={.flags=SPI_TRANS_USE_TXDATA,.length=16};
    t.tx_data[0]=reg; t.tx_data[1]=value;
    return spi_device_polling_transmit(imu[id],&t);
}
static esp_err_t reg_read(unsigned id,uint8_t reg,uint8_t *data,size_t n) {
    uint8_t tx[2049]={0},rx[2049];
    if(n>2048) return ESP_ERR_INVALID_SIZE;
    tx[0]=reg|0x80;
    spi_transaction_t t={.length=(n+1)*8,.tx_buffer=tx,.rx_buffer=rx};
    TRY(spi_device_polling_transmit(imu[id],&t)); memcpy(data,rx+1,n); return ESP_OK;
}
static esp_err_t checked_write(unsigned id,uint8_t reg,uint8_t val) {
    uint8_t got; TRY(reg_write(id,reg,val)); TRY(reg_read(id,reg,&got,1));
    return got==val?ESP_OK:ESP_ERR_INVALID_RESPONSE;
}
esp_err_t imu_bus_init(unsigned count) {
    if(count > 2) return ESP_ERR_INVALID_ARG;
    if(!count)return ESP_OK;
    spi_bus_config_t ib={.mosi_io_num=IMU_MOSI,.miso_io_num=IMU_MISO,
        .sclk_io_num=IMU_SCK,.quadwp_io_num=-1,.quadhd_io_num=-1,.max_transfer_sz=2049};
    TRY(spi_bus_initialize(SPI3_HOST,&ib,SPI_DMA_CH_AUTO)); // FIFO bursts can exceed the non-DMA 64-byte limit.
    for(unsigned id=0;id<count;id++) {
        spi_device_interface_config_t ic={.clock_speed_hz=1000000,.mode=0,
            .spics_io_num=id?SHANK_CS:FOOT_CS,.queue_size=1};
        TRY(spi_bus_add_device(SPI3_HOST,&ic,&imu[id]));
        TRY(reg_write(id,0x76,0)); TRY(reg_write(id,0x11,1));
        vTaskDelay(pdMS_TO_TICKS(10));
        uint8_t who; TRY(reg_read(id,0x75,&who,1));
        if(who!=0x47) return ESP_ERR_NOT_FOUND;
        TRY(checked_write(id,0x4c,0x33)); // byte count, big endian, disable I2C
        TRY(checked_write(id,0x4f,0x07)); // gyro ±2000 dps, 200 Hz
        TRY(checked_write(id,0x50,0x07)); // accel ±16 g, 200 Hz
        TRY(checked_write(id,0x51,0x16)); // gyro UI 2nd order; preserve reset decimator
        TRY(checked_write(id,0x53,0x0d)); // accel UI 2nd order
        TRY(checked_write(id,0x52,0x44)); // both UI bandwidth selector 4
        TRY(checked_write(id,0x54,0x21)); // 1 us timestamp, no FSYNC, reserved bit preserved
        TRY(checked_write(id,0x5f,0x0f)); // standard 16-byte accel+gyro+temp+time FIFO
        TRY(checked_write(id,0x14,0x03)); // INT1 pulsed, push-pull, active high
        TRY(checked_write(id,0x64,0x00)); // clear INT_ASYNC_RESET
        TRY(checked_write(id,0x65,0x08)); // UI data ready on INT1
    }
    return ESP_OK;
}
esp_err_t sensors_init(void) {
    TRY(adc_bus_init());
    return imu_bus_init(IMU_COUNT);
}
esp_err_t imu_start(unsigned id) {
    TRY(reg_write(id,0x16,0)); // FIFO bypass during startup
    TRY(reg_write(id,0x4e,0x0f)); // both sensors low-noise mode
    vTaskDelay(pdMS_TO_TICKS(50)); // gyro startup and minimum on-time
    TRY(reg_write(id,0x4b,0x02)); vTaskDelay(pdMS_TO_TICKS(2));
    TRY(reg_write(id,0x16,0x40)); return ESP_OK; // stream FIFO
}
esp_err_t imu_stop(unsigned id) {
    TRY(reg_write(id,0x16,0)); TRY(reg_write(id,0x4e,0)); return ESP_OK;
}
esp_err_t imu_fifo(unsigned id,uint8_t *data,size_t cap,size_t *packets,bool *overflow) {
    uint8_t status,count[2]; *packets=0; *overflow=false;
    TRY(reg_read(id,0x2d,&status,1));
    TRY(reg_read(id,0x2e,count,2)); unsigned bytes=(count[0]<<8)|count[1];
    if((status&0x02)||bytes>=2048) {
        *overflow=true; TRY(reg_write(id,0x4b,0x02)); return ESP_OK;
    }
    if(bytes>cap) return ESP_ERR_INVALID_SIZE;
    // A partial packet may be being written; leave it for the next poll.
    bytes=(bytes/16)*16;
    if(bytes) { TRY(reg_read(id,0x30,data,bytes)); *packets=bytes/16; }
    return ESP_OK;
}
esp_err_t battery_init(void) {
    adc_oneshot_unit_init_cfg_t unit={.unit_id=ADC_UNIT_1};
    TRY(adc_oneshot_new_unit(&unit,&battery_adc));
    adc_oneshot_chan_cfg_t ch={.atten=ADC_ATTEN_DB_12,.bitwidth=ADC_BITWIDTH_DEFAULT};
    TRY(adc_oneshot_config_channel(battery_adc,ADC_CHANNEL_0,&ch));
    adc_cali_curve_fitting_config_t cal={.unit_id=ADC_UNIT_1,.chan=ADC_CHANNEL_0,
        .atten=ADC_ATTEN_DB_12,.bitwidth=ADC_BITWIDTH_DEFAULT};
    return adc_cali_create_scheme_curve_fitting(&cal,&battery_cal);
}
int battery_mv(void) {
    int raw,mv,total=0;
    for(int i=0;i<16;i++) {
        if(adc_oneshot_read(battery_adc,ADC_CHANNEL_0,&raw)!=ESP_OK ||
           adc_cali_raw_to_voltage(battery_cal,raw,&mv)!=ESP_OK) return -1;
        total+=mv;
    }
    return (int)((total/16.0f)*BATTERY_DIVIDER);
}
