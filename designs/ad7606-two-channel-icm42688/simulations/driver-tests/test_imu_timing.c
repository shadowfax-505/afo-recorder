#include <assert.h>
#include <stdio.h>
#include "../../firmware/main/imu_timing.h"
int main(void){
    imu_clock_t c={0};uint64_t time;bool gap;
    assert(imu_clock_step(&c,65530,100000,101000,&time,&gap)&&time==100000&&!gap);
    assert(imu_clock_step(&c,4994,90000,106000,&time,&gap)&&time==105000&&!gap);
    puts("PASS first IRQ anchor and sensor-counter rollover");
    assert(imu_clock_step(&c,9994,99000,111000,&time,&gap)&&time==110000&&!gap);
    puts("PASS interrupt re-anchoring cannot regress reconstructed sample time");
    for(unsigned i=1;i<=8000;i++)assert(imu_clock_step(&c,(uint16_t)(9994+i*5000),0,
        111000+(uint64_t)i*5000,&time,&gap)&&time==110000+(uint64_t)i*5000&&!gap);
    puts("PASS 40s counter continuity across repeated 16-bit rollovers");
    imu_clock_t other={0};
    assert(imu_clock_step(&other,5000,500000,501000,&time,&gap)&&time==500000);
    assert(other.estimated_us!=c.estimated_us);puts("PASS independent foot and shank clocks");
    assert(imu_clock_step(&other,15000,0,511000,&time,&gap)&&time==510000&&gap);
    puts("PASS missing sample interval is explicitly flagged");
    assert(!imu_clock_step(&other,15000,0,512000,&time,&gap));
    assert(!imu_clock_step(&other,25001,0,521001,&time,&gap));
    puts("PASS duplicate and implausible sensor intervals are rejected");
    assert(!imu_clock_step(&other,20000,0,576536,&time,&gap));
    assert(!imu_clock_step(&other,20000,0,510999,&time,&gap));
    puts("PASS long rollover ambiguity and regressed read time are rejected");
    other.estimated_us=UINT64_MAX-100;
    assert(!imu_clock_step(&other,20000,0,516000,&time,&gap));
    puts("PASS 64-bit estimate overflow cannot create a plausible timestamp");
    return 0;
}
