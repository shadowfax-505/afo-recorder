#include "sensors.h"
#include "mpu_timing.h"
#include "board.h"
#include <string.h>
#include "driver/i2c_master.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#define TRY(x) do { esp_err_t e=(x); if(e!=ESP_OK) return e; } while(0)
static i2c_master_dev_handle_t imu[2];
static adc_oneshot_unit_handle_t battery_adc;
static adc_cali_handle_t battery_cal;
static esp_err_t reg_write(unsigned id,uint8_t reg,uint8_t value) {
    if(id>=2||!imu[id])return ESP_ERR_INVALID_ARG;
    uint8_t tx[]={reg,value};return i2c_master_transmit(imu[id],tx,2,50);
}
static esp_err_t reg_read(unsigned id,uint8_t reg,uint8_t *data,size_t n) {
    if(id>=2||!imu[id]||!data)return ESP_ERR_INVALID_ARG;
    return i2c_master_transmit_receive(imu[id],&reg,1,data,n,50);
}
static esp_err_t checked_write(unsigned id,uint8_t reg,uint8_t val) {
    uint8_t got;TRY(reg_write(id,reg,val));TRY(reg_read(id,reg,&got,1));
    return got==val?ESP_OK:ESP_ERR_INVALID_RESPONSE;
}
esp_err_t imu_bus_init(unsigned count) {
    if(count>2)return ESP_ERR_INVALID_ARG;
    if(!count)return ESP_OK;
    // Establish distinct addresses before the first bus transaction. Do not also strap AD0.
    gpio_config_t addr={.pin_bit_mask=(1ULL<<FOOT_AD0)|(1ULL<<SHANK_AD0),.mode=GPIO_MODE_OUTPUT};
    TRY(gpio_config(&addr));TRY(gpio_set_level(FOOT_AD0,0));TRY(gpio_set_level(SHANK_AD0,1));
    vTaskDelay(pdMS_TO_TICKS(10));
    i2c_master_bus_config_t cfg={.i2c_port=I2C_NUM_0,.sda_io_num=IMU_SDA,.scl_io_num=IMU_SCL,
        .clk_source=I2C_CLK_SRC_DEFAULT,.glitch_ignore_cnt=7,.flags.enable_internal_pullup=false};
    i2c_master_bus_handle_t bus;TRY(i2c_new_master_bus(&cfg,&bus));
    for(unsigned id=0;id<count;id++) {
        i2c_device_config_t dev={.dev_addr_length=I2C_ADDR_BIT_LEN_7,.device_address=0x68+id,.scl_speed_hz=400000};
        TRY(i2c_master_bus_add_device(bus,&dev,&imu[id]));
        uint8_t who;TRY(reg_read(id,0x75,&who,1));if(who!=0x68)return ESP_ERR_NOT_FOUND;
        TRY(reg_write(id,0x6b,0x80));vTaskDelay(pdMS_TO_TICKS(100));
        TRY(checked_write(id,0x6b,0x01)); // PLL X gyro, awake
        TRY(checked_write(id,0x6c,0));
        TRY(checked_write(id,0x1a,3)); // DLPF: gyro 42 Hz, accel 44 Hz
        TRY(checked_write(id,0x19,4)); // 1 kHz / (4+1) = 200 Hz
        TRY(checked_write(id,0x1b,0x18)); // +/-2000 dps
        TRY(checked_write(id,0x1c,0x18)); // +/-16 g
        TRY(checked_write(id,0x37,0)); // pulsed, active-high, push-pull INT
        TRY(checked_write(id,0x38,0));TRY(checked_write(id,0x23,0));
        TRY(checked_write(id,0x6a,0));
    }
    return ESP_OK;
}
esp_err_t sensors_init(void){TRY(adc_bus_init());return imu_bus_init(IMU_COUNT);}
esp_err_t imu_start(unsigned id) {
    TRY(reg_write(id,0x6b,1));vTaskDelay(pdMS_TO_TICKS(100));
    TRY(reg_write(id,0x38,0));TRY(reg_write(id,0x23,0));TRY(reg_write(id,0x6a,0x04));
    vTaskDelay(pdMS_TO_TICKS(2));uint8_t status;TRY(reg_read(id,0x3a,&status,1));
    TRY(reg_write(id,0x6a,0x40));TRY(reg_write(id,0x23,0x78)); // accel XYZ then gyro XYZ, 12 bytes
    return reg_write(id,0x38,0x11); // data ready + FIFO overflow
}
esp_err_t imu_stop(unsigned id) {
    TRY(reg_write(id,0x38,0));TRY(reg_write(id,0x23,0));TRY(reg_write(id,0x6a,0));
    return reg_write(id,0x6b,0x40);
}
esp_err_t imu_fifo(unsigned id,uint8_t *data,size_t cap,size_t *packets,bool *overflow) {
    uint8_t status,cnt[2];*packets=0;*overflow=false;
    TRY(reg_read(id,0x3a,&status,1));TRY(reg_read(id,0x72,cnt,2));
    unsigned bytes=((unsigned)cnt[0]<<8)|cnt[1];
    if(mpu_overflow(status,bytes)){*overflow=true;TRY(reg_write(id,0x23,0));TRY(reg_write(id,0x6a,0));TRY(reg_write(id,0x6a,4));vTaskDelay(pdMS_TO_TICKS(2));TRY(reg_write(id,0x6a,0x40));TRY(reg_write(id,0x23,0x78));return ESP_OK;}
    bytes=mpu_complete_bytes(bytes);if(bytes>cap)return ESP_ERR_INVALID_SIZE;
    if(bytes){TRY(reg_read(id,0x74,data,bytes));*packets=bytes/12;}
    // An overflow during the read invalidates the entire batch.
    TRY(reg_read(id,0x3a,&status,1));if(status&0x10){*overflow=true;*packets=0;}
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
