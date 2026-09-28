#!/usr/bin/env python3
"""Synthetic Rev B timing/queue model; not ESP32 execution or battery validation."""
from pathlib import Path
import sys,json,math,heapq,collections,binascii,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'host'))
from afo_format import EMG_B,IMU,FIFO,STATUS,make_header,make_record
from convert import convert

def metadata(count):
 return dict(hardware_design='AD7606_TWO_FIXED' if count==2 else 'LEGACY_FOUR_CHANNEL_TEST_FIXTURE',schema='afo-recorder/3',adc_model='AD7606',adc_sensor_crc_supported=False,timestamp_event='conversion_trigger',firmware='B.0.1-software-model',synthetic=True,emg_hz=8000,imu_hz=200,imu_enabled=True,adc_bits=16,adc_reference_mv=5000,adc_reference_measured=False,active_channel_count=count,emg_channels=[f'EMG{i+1}' for i in range(count)],adc_pga=1,input_scale=1,input_midpoint_mv=0,calibration_state='uncalibrated',adc_clock_hz=0,adc_osr=1,adc_filter='oversampling disabled; internal analog filter',simultaneous=True,accel_range_g=16,gyro_range_dps=2000,imu_timestamp_tick_us=1,record_bytes=64,notes='SYNTHETIC queue/clock model. No physical measurements. Channel labels are ports, not verified muscle placements.')

def frame(seq,t,count,slots=1):
 values=[int((1.5+.20*math.sin(2*math.pi*(71+23*i)*t/1e6)+.035*math.sin(2*math.pi*50*t/1e6))/(5/32768)) for i in range(count)]+[0]*(4-count)
 mask=(1<<count)-1
 status=0
 raw=status.to_bytes(2,'big')+b'\0'+b''.join((v&0xffffff).to_bytes(3,'big') for v in values)
 crc=0
 return make_record(7,seq,t,EMG_B.pack(*values,status,crc,18,slots,mask,t+3),1 if slots>1 else 0)

def generate(path,count=2,scenario='normal',duration=2):
 meta=metadata(count);queue=collections.deque();saved=[];events=[];produced=[0,0,0];high=0;dropped=0;missed=0;adc_errors=0;lasttime=0;reason=0;busy_until=0
 for seq in range(1,int(duration*8000)+1):heapq.heappush(events,(seq*125,0,seq))
 for i,ppm in enumerate([70,-110]):
  period=5000*(1+ppm/1e6)
  for seq in range(1,int(duration*200)+1):heapq.heappush(events,(int(seq*period+100+140*i),i+1,seq))
 while events:
  t,kind,seq=heapq.heappop(events)
  if t>duration*1e6:break
  lasttime=t
  if scenario=='interrupted' and t>=1200000:break
  if scenario=='missing_imu' and kind==2:continue
  if scenario=='missing_emg' and kind==0 and seq==4000:missed+=1;continue
  if scenario=='busy_timeout' and kind==0 and seq==6000:adc_errors=1;reason=3;break
  if t>=busy_until:
   saved.extend(queue);queue.clear()
  if scenario in ['delayed_write','overflow'] and 500000<=t<500126 and busy_until<t+1:
   busy_until=t+(120000 if scenario=='delayed_write' else 500000)
  if kind==0:
   slots=2 if scenario=='missing_emg' and seq==4001 else 1
   rec=frame(seq,t,count,slots)
  else:
   raw=FIFO.pack(0x68,0,0,2048,0,0,0,25,t&65535)
   rec=make_record(kind+1,seq,t,IMU.pack(raw,t+3,t+35,t),2)
  produced[kind]+=1
  if len(queue)>=2048:dropped+=1;reason=2;break
  queue.append(rec);high=max(high,len(queue))
 if scenario!='interrupted':saved.extend(queue)
 else:
  # Power interruption loses unflushed block and a partial record tail.
  if saved:saved=saved[:-10]
 status=STATUS.pack(missed,dropped,0,0,adc_errors,*produced,3800,high)
 if scenario!='interrupted':saved.append(make_record(5,1,lasttime+100,status,reason))
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(make_header(meta)+b''.join(saved)+(b'AFR1\x06'+bytes(12) if scenario=='interrupted' else b''))
 return dict(scenario=scenario,active_channels=count,produced=produced,queue_high_water=high,queue_capacity=2048,dropped=dropped,stop_reason=reason,read_transfer_us=18,independent_imu_ppm=[70,-110])

def main():
 out=ROOT/'examples'/'simulated';out.mkdir(parents=True,exist_ok=True);results=[]
 for count in (2,):
  for scenario in ['normal','delayed_write','overflow','missing_imu','missing_emg','busy_timeout','interrupted']:
   name=f'{count}ch-{scenario}';file=out/(name+'.afolog');info=generate(file,count,scenario)
   export=out/(name+'-csv')
   if export.exists():shutil.rmtree(export)
   report=convert(file,export,recover=scenario=='interrupted',make_plots=scenario=='normal')
   expected=scenario in ['normal','delayed_write']
   assert report['no_detected_sample_loss']==expected,(name,report)
   info.update(no_detected_sample_loss=report['no_detected_sample_loss'],issues=report['issues']);results.append(info)
 (ROOT/'simulations'/'acquisition-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print('Passed',len(results),'software scenarios. Not hardware validation.')
if __name__=='__main__':main()
