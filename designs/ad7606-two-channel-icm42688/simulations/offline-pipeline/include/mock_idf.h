#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_INVALID_STATE 1
#define ESP_ERR_TIMEOUT 2
#define ESP_FAIL 3
#define SPI2_HOST 2
#define SPI_DMA_DISABLED 0
#define GPIO_MODE_OUTPUT 1
#define GPTIMER_CLK_SRC_DEFAULT 0
#define GPTIMER_COUNT_UP 0
#define portMUX_INITIALIZER_UNLOCKED 0
#define pdMS_TO_TICKS(x) (x)
typedef int portMUX_TYPE;
#define portENTER_CRITICAL_ISR(x) ((void)(x))
#define portEXIT_CRITICAL_ISR(x) ((void)(x))
#define portENTER_CRITICAL(x) ((void)(x))
#define portEXIT_CRITICAL(x) ((void)(x))
typedef void *spi_device_handle_t;
typedef void *gptimer_handle_t;
typedef struct { int unused; } gptimer_alarm_event_data_t;
typedef struct {uint64_t pin_bit_mask; int mode;} gpio_config_t;
typedef struct {int mosi_io_num,miso_io_num,sclk_io_num,quadwp_io_num,quadhd_io_num,max_transfer_sz;} spi_bus_config_t;
typedef struct {int clock_speed_hz,mode,spics_io_num,queue_size;} spi_device_interface_config_t;
typedef struct {size_t length;void *rx_buffer;const void *tx_buffer;unsigned flags;uint8_t tx_data[4];} spi_transaction_t;
typedef struct {int clk_src,direction,resolution_hz,intr_priority;} gptimer_config_t;
typedef struct {bool (*on_alarm)(gptimer_handle_t,const gptimer_alarm_event_data_t *,void *);} gptimer_event_callbacks_t;
typedef struct {uint64_t alarm_count,reload_count;struct {bool auto_reload_on_alarm;} flags;} gptimer_alarm_config_t;
esp_err_t gpio_config(const gpio_config_t *);
int gpio_set_level(int,int);
int gpio_get_level(int);
esp_err_t spi_bus_initialize(int,const spi_bus_config_t *,int);
esp_err_t spi_bus_add_device(int,const spi_device_interface_config_t *,spi_device_handle_t *);
esp_err_t spi_device_polling_transmit(spi_device_handle_t,spi_transaction_t *);
esp_err_t gptimer_new_timer(const gptimer_config_t *,gptimer_handle_t *);
esp_err_t gptimer_register_event_callbacks(gptimer_handle_t,const gptimer_event_callbacks_t *,void *);
esp_err_t gptimer_set_alarm_action(gptimer_handle_t,const gptimer_alarm_config_t *);
esp_err_t gptimer_enable(gptimer_handle_t);
esp_err_t gptimer_set_raw_count(gptimer_handle_t,uint64_t);
esp_err_t gptimer_start(gptimer_handle_t);
esp_err_t gptimer_stop(gptimer_handle_t);
int64_t esp_timer_get_time(void);
void esp_rom_delay_us(unsigned);
void vTaskDelay(unsigned);

#define SPI3_HOST 3
#define SPI_DMA_CH_AUTO 1
#define SPI_TRANS_USE_TXDATA 1
#define ESP_ERR_INVALID_SIZE 4
#define ESP_ERR_INVALID_ARG 5
#define ESP_ERR_INVALID_RESPONSE 6
#define ESP_ERR_NOT_FOUND 7
#define ADC_UNIT_1 1
#define ADC_CHANNEL_0 0
#define ADC_ATTEN_DB_12 12
#define ADC_BITWIDTH_DEFAULT 0
#define ESP_INTR_FLAG_LEVEL2 (1<<2)
typedef void *adc_oneshot_unit_handle_t;
typedef void *adc_cali_handle_t;
typedef struct {int unit_id;} adc_oneshot_unit_init_cfg_t;
typedef struct {int atten,bitwidth;} adc_oneshot_chan_cfg_t;
typedef struct {int unit_id,chan,atten,bitwidth;} adc_cali_curve_fitting_config_t;
esp_err_t adc_oneshot_new_unit(const adc_oneshot_unit_init_cfg_t *,adc_oneshot_unit_handle_t *);
esp_err_t adc_oneshot_config_channel(adc_oneshot_unit_handle_t,int,const adc_oneshot_chan_cfg_t *);
esp_err_t adc_cali_create_scheme_curve_fitting(const adc_cali_curve_fitting_config_t *,adc_cali_handle_t *);
esp_err_t adc_oneshot_read(adc_oneshot_unit_handle_t,int,int *);
esp_err_t adc_cali_raw_to_voltage(adc_cali_handle_t,int,int *);
