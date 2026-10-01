#pragma once
#include "driver/gpio.h"
int qemu_model_gpio_get_level(gpio_num_t pin);
void qemu_model_configure(unsigned selector,unsigned adc_fault,unsigned imu_fault);
void qemu_fixture_main(void);
