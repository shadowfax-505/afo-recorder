#pragma once
#include <stdint.h>
#include <stdbool.h>
/* Pure helpers shared by the firmware and native fault tests. */
static inline bool mpu_overflow(uint8_t status,unsigned bytes){return (status&0x10)||bytes>=1024;}
static inline unsigned mpu_complete_bytes(unsigned bytes){return (bytes/12)*12;}
static inline uint64_t mpu_estimate(uint64_t anchor,unsigned index,unsigned count){
    uint64_t lag=(uint64_t)(count-1-index)*5000;return anchor>=lag?anchor-lag:0;
}
static inline uint8_t mpu_time_flags(uint64_t anchor,unsigned count,uint32_t irq_delta,bool raced){
    return 2 | ((raced||irq_delta!=count||anchor<(uint64_t)(count-1)*5000)?1:0);
}
