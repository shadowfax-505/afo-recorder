#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include "esp_err.h"
esp_err_t sensors_init(void);
esp_err_t emg_frame(int32_t codes[4], uint16_t *status, uint16_t *crc);
esp_err_t adc_configure(void);
esp_err_t imu_start(unsigned id);
esp_err_t imu_stop(unsigned id);
esp_err_t imu_fifo(unsigned id, uint8_t *data, size_t capacity, size_t *packets, bool *overflow);
esp_err_t battery_init(void);
int battery_mv(void);

esp_err_t adc_bus_init(void);
esp_err_t imu_bus_init(unsigned count);

esp_err_t adc_stream_start(void);
void adc_stream_stop(void);
uint64_t adc_sample_timestamp(void);
