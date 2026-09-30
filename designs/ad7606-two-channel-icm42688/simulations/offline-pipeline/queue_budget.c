// Event-count model only. No firmware/RTOS/storage execution or measured speed.
#include "../../firmware/main/board.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
int main(int argc,char **argv){
    assert(argc==5);double duration=atof(argv[1])*1e6,throughput=atof(argv[2]);
    double stall=atof(argv[3])*1000,stall_period=atof(argv[4])*1e6;
    assert(duration>0&&throughput>0&&stall>=0&&stall_period>0);
    double next[3]={125,5000*(1+70e-6),5000*(1-110e-6)};
    double period[3]={125,5000*(1+70e-6),5000*(1-110e-6)};
    double write_at=INFINITY,next_stall=stall_period,t=0;
    uint64_t produced[3]={0},consumed=0,writes=0;unsigned queued=0,high=0,block=0,reason=0;
    while(t<duration){
        unsigned kind=0;for(unsigned i=1;i<3;i++)if(next[i]<next[kind])kind=i;
        if(write_at<=next[kind]){t=write_at;write_at=INFINITY;writes++;}
        else {
            t=next[kind];if(t>duration)break;
            next[kind]+=period[kind];produced[kind]++;
            if(queued==RECORD_QUEUE_LENGTH){reason=2;break;}
            queued++;if(queued>high)high=queued;
        }
        if(!isfinite(write_at))while(queued){
            queued--;consumed++;block++;
            if(block==128){
                double delay=8192/throughput*1e6+1000;
                if(t>=next_stall){delay+=stall;next_stall+=stall_period;}
                write_at=t+delay;block=0;break;
            }
        }
    }
    printf("{\"hardware_measured\":false,\"firmware_executed\":false,\"duration_s\":%.0f,"
        "\"modeled_write_bytes_s\":%.0f,\"extra_stall_ms\":%.0f,\"stall_period_s\":%.0f,"
        "\"produced\":[%llu,%llu,%llu],\"queue_high_water\":%u,\"queue_capacity\":%u,"
        "\"consumed\":%llu,\"completed_writes\":%llu,\"stop_reason\":%u,\"last_event_s\":%.6f}\n",
        duration/1e6,throughput,stall/1000,stall_period/1e6,
        (unsigned long long)produced[0],(unsigned long long)produced[1],(unsigned long long)produced[2],high,
        RECORD_QUEUE_LENGTH,(unsigned long long)consumed,(unsigned long long)writes,reason,t/1e6);
    return 0;
}
