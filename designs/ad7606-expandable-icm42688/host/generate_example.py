#!/usr/bin/env python3
"""Generate explicitly synthetic test data; this is not a participant recording."""
import argparse
import math
from pathlib import Path
from afo_format import make_header, make_record, EMG, IMU, FIFO, STATUS

def generate(path: Path, seconds: float=2.0, *, skip_slot: int=0, imu_enabled: bool=True):
    metadata={'schema':'afo-recorder/1','firmware':'synthetic-generator/1','synthetic':True,
        'trial_id':'SYNTHETIC_DEMO','clock':'esp_timer_boot_us','emg_hz':8000,'imu_hz':200,
        'imu_enabled':imu_enabled,'adc_bits':12,'adc_reference_mv':3300,'adc_reference_measured':False,
        'accel_range_g':16,'gyro_range_dps':2000,'imu_timestamp_tick_us':1,
        'imu_timing_calibrated':False,'record_bytes':64,
        'emg_channels':['tibialis_anterior','medial_gastrocnemius'],
        'imu_locations':['foot','shank'],'notes':'Synthetic signals only; no hardware or human validation.'}
    if not 0<seconds<=7200:raise ValueError('duration must be >0 and <=7200 seconds')
    emg_n=0;imu_n=0;missed=0
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:
        f.write(make_header(metadata))
        for slot in range(1,int(seconds*8000)+1):
            t=slot/8000;host=1000000+slot*125
            if slot==skip_slot:missed+=1
            else:
                a=round(2048+(120+180*(.5+.5*math.sin(2*math.pi*t)))*math.sin(2*math.pi*85*t))
                b=round(2048+220*math.sin(2*math.pi*125*t+.8))
                slots=2 if slot==skip_slot+1 and skip_slot else 1
                f.write(make_record(1,slot,host,EMG.pack(a,b,25,27,25,slots),int(slots>1)))
                emg_n+=1
            if slot%40==0 and imu_enabled:
                imu_n+=1
                for kind in (2,3):
                    raw=[round(300*math.sin(2*math.pi*t)),round(120*math.cos(2*math.pi*t)),2048,
                         round(500*math.sin(2*math.pi*t)),0,round(80*math.cos(2*math.pi*t))]
                    packet=FIFO.pack(0x68,*raw,0,(imu_n*5000)&0xffff)
                    f.write(make_record(kind,imu_n,host,IMU.pack(packet,host+20,host+160,host),2))
        f.write(make_record(5,1,1000000+int(seconds*1e6)+200,
                           STATUS.pack(missed,0,0,0,0,emg_n,imu_n,imu_n,3850,16)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    p.add_argument('--seconds',type=float,default=2);args=p.parse_args();generate(args.output,args.seconds)
