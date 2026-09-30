#!/usr/bin/env python3
"""Check the recorder's eight-channel Wokwi logic-analyzer trace, in nanoseconds."""
import json
from pathlib import Path
import statistics
import re

WORDS = [6554,13107,-1234,2345,-32768,32767,0,1111]

def verify(path, case='normal'):
    signals, state = {}, {}
    now, frame, first_conv = 0, None, None
    conv, widths, busy_widths, frames, warmup = [], [], [], [], []
    conv_start = busy_start = None
    rising = [0] * 8
    with Path(path).open() as stream:
        for line in stream:
            line = line.strip()
            m = re.match(r'\$var\s+\S+\s+1\s+(\S+)\s+D([0-7])\b',line)
            if m: signals[m[1]] = int(m[2]); continue
            if line.startswith('$timescale') and '1ns' not in line.replace(' ',''):
                raise ValueError('This parser requires the Wokwi 1 ns timescale')
            if re.fullmatch(r'#\d+',line): now=int(line[1:]);continue
            if len(line)<2 or line[0] not in '01' or line[1:] not in signals: continue
            channel=signals[line[1:]]; value=int(line[0]);old=state.get(channel);state[channel]=value
            if old is None or old==value:continue
            if value:rising[channel]+=1
            if channel==0:
                if value:
                    conv.append(now);conv_start=now
                    if first_conv is None:first_conv=now
                elif conv_start is not None:widths.append(now-conv_start);conv_start=None
            if channel==1 and first_conv is not None:
                if value:busy_start=now
                elif busy_start is not None:busy_widths.append(now-busy_start);busy_start=None
            if channel==2:
                if not value:frame={'start_ns':now,'bits':[],'rises':0,'measured':first_conv is not None}
                elif frame is not None:
                    bits=frame.pop('bits');frame['falls']=len(bits);frame['duration_ns']=now-frame['start_ns']
                    unsigned=[int(''.join(map(str,bits[i:i+16])),2) for i in range(0,len(bits)-15,16)]
                    frame['words']=[x if x<32768 else x-65536 for x in unsigned]
                    (frames if frame.pop('measured') else warmup).append(frame);frame=None
            if channel==3 and frame is not None:
                if value:frame['rises']+=1
                else:frame['bits'].append(state.get(4,0))
    periods=[b-a for a,b in zip(conv,conv[1:]) if b-a<200000]
    errors=[]
    expected=[-1]*8 if case=='incorrect-mode' else WORDS
    if set(signals.values())!=set(range(8)):errors.append('Missing analyzer channels')
    if len(warmup)!=1:errors.append('Expected one reset-time SPI priming read')
    for i,f in enumerate(frames):
        if f['rises']!=128 or f['falls']!=128:errors.append(f'Frame {i}: wrong clock count')
        if f['words']!=expected:errors.append(f'Frame {i}: wrong signed eight-word order')
    if case in ('normal','incorrect-mode'):
        if len(frames)<1000:errors.append('Too few acquisition frames')
        if not periods or min(periods)<120000 or max(periods)>130000:errors.append('Individual trigger interval outside 125 us +/-5 us')
        if periods and not 7920 <= 1e9/statistics.mean(periods) <= 8080:errors.append('Mean conversion rate outside 8 kHz +/-1%')
        if not busy_widths or min(busy_widths)!=4000 or max(busy_widths)!=4000:errors.append('Behavioral BUSY duration differs from 4 us')
        if not widths or min(widths)<25:errors.append('CONVST pulse shorter than 25 ns')
        if not rising[5] or (case=='normal' and not rising[6]):errors.append('Missing IMU interrupt activity')
    elif case=='stuck-busy':
        if len(conv)!=1 or frames or busy_widths or state.get(1)!=1:errors.append('Expected one conversion with BUSY latched high and no read')
    elif case=='delayed-busy':
        if len(conv)!=1 or frames or busy_widths!=[250000]:errors.append('Expected 250 us BUSY, no read and stopped triggers')
    elif case=='absent-shank' and (conv or frames):errors.append('ADC acquisition began despite failed IMU initialization')
    elif case=='missed-interrupt' and rising[5]:errors.append('Missing-interrupt fault produced foot interrupt edges')
    report={'case':case,'pass':not errors,'hardware_measured':False,
            'engine':'Wokwi ESP32-S3 VCD protocol analysis','priming_reads':len(warmup),
            'conversion_triggers':len(conv),'complete_adc_frames':len(frames),
            'partial_frame_at_trace_end':frame is not None,'trace_end_ns':now,
            'pulse_width_ns':{'min':min(widths) if widths else None,'max':max(widths) if widths else None},
            'busy_width_ns':sorted(set(busy_widths)),
            'conversion_period_ns':{'min':min(periods) if periods else None,'median':statistics.median(periods) if periods else None,'max':max(periods) if periods else None},
            'coverage_note':'Analyzer buffer may end before serial run; partial final SPI frame is excluded from decoding',
            'imu_rising_edges':rising[5:7],'errors':errors[:20],'total_errors':len(errors)}
    return report

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('vcd');parser.add_argument('--case',default='normal');args=parser.parse_args()
    result=verify(args.vcd,args.case);print(json.dumps(result,indent=2));raise SystemExit(not result['pass'])
