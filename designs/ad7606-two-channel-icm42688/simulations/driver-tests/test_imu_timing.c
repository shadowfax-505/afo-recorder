#include <assert.h>
#include <stdio.h>
#include "../../firmware/main/imu_timing.h"
// A 200 Hz ICM-42688 stream advances 4687.5 ticks of 32/30 us per 5000 us sample.
static uint16_t step_ticks(unsigned i){return i%2?4688:4687;}
int main(void){
    imu_clock_t c={0};uint64_t time;bool gap;uint64_t total=0;uint16_t counter=65530;
    assert(imu_ticks_to_us(15)==16&&imu_ticks_to_us(4688)==5000&&imu_ticks_to_us(65536)==69905);
    puts("PASS 32/30 us tick conversion");
    assert(imu_clock_step(&c,counter,100000,101000,&time,&gap)&&time==100000&&!gap);
    counter+=4688;total+=4688;
    assert(imu_clock_step(&c,counter,90000,106000,&time,&gap)&&time==100000+imu_ticks_to_us(total)&&!gap);
    puts("PASS first IRQ anchor and sensor-counter rollover");
    counter+=4687;total+=4687;
    assert(imu_clock_step(&c,counter,99000,111000,&time,&gap)&&time==100000+imu_ticks_to_us(total)&&!gap);
    puts("PASS interrupt re-anchoring cannot regress reconstructed sample time");
    for(unsigned i=1;i<=8000;i++){
        counter+=step_ticks(i);total+=step_ticks(i);
        assert(imu_clock_step(&c,counter,0,111000+(uint64_t)i*5000,&time,&gap)&&!gap);
        assert(time==100000+imu_ticks_to_us(total));
    }
    // 8002 samples at 4687.5 ticks each span 40,010 ms with no rounding drift.
    assert(time>=100000+8002ull*5000-1&&time<=100000+8002ull*5000+1);
    puts("PASS 40s counter continuity across repeated 16-bit rollovers without rounding drift");
    imu_clock_t other={0};
    assert(imu_clock_step(&other,5000,500000,501000,&time,&gap)&&time==500000);
    assert(other.estimated_us!=c.estimated_us);puts("PASS independent foot and shank clocks");
    assert(imu_clock_step(&other,5000+9375,0,511000,&time,&gap)&&time==500000+imu_ticks_to_us(9375)&&gap);
    puts("PASS missing sample interval is explicitly flagged");
    assert(!imu_clock_step(&other,5000+9375,0,512000,&time,&gap));
    assert(!imu_clock_step(&other,5000+9375+10001,0,521001,&time,&gap));
    puts("PASS duplicate and implausible sensor intervals are rejected");
    assert(!imu_clock_step(&other,(uint16_t)(5000+9375+4688),0,576536,&time,&gap));
    assert(!imu_clock_step(&other,(uint16_t)(5000+9375+4688),0,510999,&time,&gap));
    puts("PASS long rollover ambiguity and regressed read time are rejected");
    other.estimated_us=UINT64_MAX-100;
    assert(!imu_clock_step(&other,(uint16_t)(5000+9375+4688),0,516000,&time,&gap));
    puts("PASS 64-bit estimate overflow cannot create a plausible timestamp");
    return 0;
}
