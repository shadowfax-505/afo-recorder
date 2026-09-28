#!/usr/bin/env python3
"""Synthetic MPU6050/ADC recordings; not measured hardware or participant data."""
import argparse,math,struct
from pathlib import Path
from afo_format import make_header,make_record,EMG_B,IMU,STATUS

def generate(path,channels=2,seconds=.25,fault='none'):
    package=Path(__file__).resolve().parents[1].name
    if channels not in (2,4) or ('-two-' in package and channels!=2):raise ValueError('unsupported physical channel count')
    if not 0<seconds<=60:raise ValueError('duration must be 0..60 seconds')
    ad='ad7606' in package
    m=dict(schema='afo-recorder/3' if ad else 'afo-recorder/2',adc_model='AD7606' if ad else 'ADS131M04',adc_bits=16 if ad else 24,adc_reference_mv=5000 if ad else 1200,adc_pga=1,adc_osr=1 if ad else 512,adc_clock_hz=0 if ad else 8192000,input_scale=1 if ad else .5,input_midpoint_mv=0 if ad else 1500,adc_sensor_crc_supported=not ad,emg_hz=8000,imu_hz=200,active_channel_count=channels,emg_channels=['EMG'+str(i+1) for i in range(channels)],record_bytes=64,calibration_state='uncalibrated',accel_range_g=16,gyro_range_dps=2000,imu_model='MPU6050',imu_packet_format='mpu6050-fifo12-batch-v1',imu_timestamp_tick_us=None,imu_timing_method='irq-anchor-nominal-period-estimate',imu_dlpf_cfg=3,imu_sample_rate_divider=4,imu_addresses=[104,105],accel_lsb_per_g=2048,gyro_lsb_per_dps=16.4,synthetic=True,hardware_variant=package,notes='Synthetic software fixture; ADC serial CRC and hardware not exercised.')
    out=bytearray(make_header(m));nimu=0;foot=0
    for n in range(1,int(seconds*8000)+1):
        t=n*125;v=[int(1000*math.sin(n/20+i)) for i in range(channels)]+[0]*(4-channels)
        out+=make_record(7 if ad else 6,n,t,EMG_B.pack(*v,0,0,15,1,(1<<channels)-1,t+2))
        if n%40==0:
            nimu+=1
            for kind in (8,9):
                if fault=='missing-sample' and kind==8 and nimu==2:continue
                packet=struct.pack('>6h',100,-100,2048,164,0,-164)+struct.pack('<HH',0,1)
                flags=3 if fault=='irq-gap' and nimu==2 else 2
                out+=make_record(kind,nimu,t,IMU.pack(packet,t+10,t+450,t),flags)
                if kind==8:foot+=1
    overflow=int(fault=='overflow')
    out+=make_record(5,1,int(seconds*1e6)+1000,STATUS.pack(0,0,0,overflow,0,int(seconds*8000),foot,nimu,3800,10),3 if overflow else 0)
    if fault=='truncated':out=out[:-9]
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(out)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--channels',type=int,default=2);p.add_argument('--seconds',type=float,default=.25);p.add_argument('--fault',choices=['none','missing-sample','irq-gap','overflow','truncated'],default='none');a=p.parse_args();generate(a.output,a.channels,a.seconds,a.fault)
