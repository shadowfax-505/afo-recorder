#pragma once
/* Register-level behavioral model of one ICM-42688-P on a 4-wire SPI bus.
 * Rules are taken from DS-000347 register descriptions (reset values,
 * reserved bits, valid codes, reset and power-on timing, FIFO packet 3 layout,
 * interrupt configuration). It is a test oracle for the production driver,
 * not a substitute for the physical sensor. */
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef struct {
    const char *name;
    uint8_t reg[128];
    double now_us,reset_until_us,write_blackout_until_us,gyro_on_us,accel_on_us;
    double next_odr_us,period_us,clock_ppm,tick_acc;
    uint16_t tick;
    uint8_t fifo[2048];size_t used;double fifo_times[128];
    double popped_times[200000];size_t popped;uint16_t latched_count;bool count_latched;
    double irq_times[200000];size_t irq_count;
    double sample_times[200000];size_t samples;
    unsigned violations;char last_violation[200];
    /* Fault injection */
    bool absent;          /* SPI jumpers in I2C position or carrier missing: MISO idle */
    int stuck_addr;       /* register that ignores writes, or -1 */
    int16_t accel[3],gyro[3];int8_t temperature;
} icm_model_t;
void icm_init(icm_model_t *m,const char *name,double clock_ppm);
void icm_advance(icm_model_t *m,double now_us);
/* One SPI transaction with CS asserted for this device. mode/clock checked by caller. */
void icm_transfer(icm_model_t *m,const uint8_t *tx,uint8_t *rx,size_t bytes);
void icm_violation(icm_model_t *m,const char *what);
