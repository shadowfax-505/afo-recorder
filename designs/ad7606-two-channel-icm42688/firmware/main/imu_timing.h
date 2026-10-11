#pragma once
#include <stdbool.h>
#include <stdint.h>

// The configured ICM FIFO contains a 16-bit timestamp with TMST_RES=0. Without
// RTC/CLKIN, the datasheet requires scaling that timestamp interval by 32/30
// (DS-000347 section 12.7, Timestamp Interval Scaling: 937/938 counts per 1 ms at
// 1 kHz ODR; TDK's ICM-426xx driver applies the same PLL_SCALE_FACTOR). A 200 Hz
// stream therefore advances about 4687.5 ticks per sample. The sensor clock
// itself may differ from nominal by up to 1.5% at 25 C and 2% over temperature
// (Table 4); use the converter's fitted host time to remove that error.
#define IMU_TICK_US_NUM 32u
#define IMU_TICK_US_DEN 30u
#define IMU_TICK_US_JSON "1.0666667"

static inline uint64_t imu_ticks_to_us(uint64_t ticks) {
    return ticks*IMU_TICK_US_NUM/IMU_TICK_US_DEN;
}

// Anchor once, then preserve sensor-clock intervals across reads. Re-anchoring
// every burst can move time backwards when the IRQ and FIFO-count observations
// disagree. Elapsed ticks are converted from the anchor in one step, so integer
// rounding never accumulates. These are uncalibrated host-time estimates; raw
// IRQ/read evidence is retained.
typedef struct {
    bool initialized;
    uint16_t ticks;
    uint64_t estimated_us,last_read_us,anchor_us,elapsed_ticks;
} imu_clock_t;

static inline bool imu_clock_step(imu_clock_t *clock,uint16_t ticks,
    uint64_t first_estimate_us,uint64_t read_start_us,uint64_t *estimate,bool *gap) {
    *gap=false;
    if(!clock->initialized) {
        clock->estimated_us=clock->anchor_us=first_estimate_us;
        clock->elapsed_ticks=0;
        clock->initialized=true;
    } else {
        uint16_t delta=(uint16_t)(ticks-clock->ticks);
        // After an entire rollover without a packet, the lost cycle count is
        // unknowable. Do not manufacture a plausible timestamp. The bounds in
        // ticks (about 8.0 and 10.7 ms) separate one missing 200 Hz sample from
        // implausible intervals. Reads more than 65,536 us apart are rejected,
        // slightly earlier than one full counter wrap (about 69.9 ms).
        if(read_start_us<clock->last_read_us||
            read_start_us-clock->last_read_us>=65536||!delta||delta>10000||
            UINT64_MAX-clock->estimated_us<imu_ticks_to_us(delta))return false;
        *gap=delta>7500;
        clock->elapsed_ticks+=delta;
        clock->estimated_us=clock->anchor_us+imu_ticks_to_us(clock->elapsed_ticks);
    }
    clock->ticks=ticks;clock->last_read_us=read_start_us;
    *estimate=clock->estimated_us;return true;
}
