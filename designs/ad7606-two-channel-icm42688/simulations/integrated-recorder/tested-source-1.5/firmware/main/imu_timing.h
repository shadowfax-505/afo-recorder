#pragma once
#include <stdbool.h>
#include <stdint.h>

// The configured ICM FIFO contains a 16-bit, 1us timestamp. Anchor once,
// then preserve sensor-clock intervals across reads. Re-anchoring every burst
// can move time backwards when the IRQ and FIFO-count observations disagree.
// These are uncalibrated host-time estimates; raw IRQ/read evidence is retained.
typedef struct {
    bool initialized;
    uint16_t ticks;
    uint64_t estimated_us,last_read_us;
} imu_clock_t;

static inline bool imu_clock_step(imu_clock_t *clock,uint16_t ticks,
    uint64_t first_estimate_us,uint64_t read_start_us,uint64_t *estimate,bool *gap) {
    *gap=false;
    if(!clock->initialized) {
        clock->estimated_us=first_estimate_us;
        clock->initialized=true;
    } else {
        uint16_t delta=(uint16_t)(ticks-clock->ticks);
        // After an entire rollover without a packet, the lost cycle count is
        // unknowable. Do not manufacture a plausible timestamp. The 10ms bound
        // also rejects implausible intervals for the configured 200Hz stream.
        if(read_start_us<clock->last_read_us||
            read_start_us-clock->last_read_us>=65536||!delta||delta>10000||
            UINT64_MAX-clock->estimated_us<delta)return false;
        *gap=delta>7500;
        clock->estimated_us+=delta;
    }
    clock->ticks=ticks;clock->last_read_us=read_start_us;
    *estimate=clock->estimated_us;return true;
}
