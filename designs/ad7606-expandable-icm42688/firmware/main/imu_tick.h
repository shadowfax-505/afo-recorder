#pragma once
#include <stdint.h>
// ICM-42688 FIFO timestamps with TMST_RES=0 nominally count 1 us, but the
// internal PLL runs at 19.2 MHz instead of 20.48 MHz, so one tick lasts 32/30 us
// (TDK ICM-426xx driver, PLL_SCALE_FACTOR_Q24, when neither CLKIN/RTC nor the
// wake-up oscillator clocks the sensor). Measure on hardware; change only these
// constants if the measured tick disagrees.
#define IMU_TICK_US_NUM 32u
#define IMU_TICK_US_DEN 30u
#define IMU_TICK_US_JSON "1.0666667"
static inline uint64_t imu_ticks_to_us(uint64_t ticks){return ticks*IMU_TICK_US_NUM/IMU_TICK_US_DEN;}
