#include <assert.h>
#include <stdio.h>
#include "mpu_timing.h"
int main(void){
 assert(mpu_complete_bytes(25)==24);assert(mpu_complete_bytes(11)==0);
 assert(mpu_overflow(0,1024));assert(mpu_overflow(0x10,12));assert(!mpu_overflow(1,1020));
 assert(mpu_estimate(20000,0,3)==10000);assert(mpu_estimate(20000,2,3)==20000);
 assert(mpu_time_flags(20000,3,3,false)==2);
 assert(mpu_time_flags(20000,3,2,false)==3); /* missed interrupt */
 assert(mpu_time_flags(20000,3,3,true)==3); /* read/IRQ race */
 assert(mpu_time_flags(1000,3,3,false)==3);assert(mpu_estimate(1000,0,3)==0);
 puts("PASS: actual firmware FIFO and timing helpers (10 assertions)");
}
