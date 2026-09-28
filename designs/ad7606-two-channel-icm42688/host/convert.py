#!/usr/bin/env python3
"""Stream AFO recordings to CSV, audit JSON, and bounded-size diagnostic plots."""
from __future__ import annotations
import argparse
import csv
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
from afo_format import (read_header, iter_records, decode_fifo, EMG, IMU,
                        decode_emg_b, KINDS, HEADER_SIZE, RECORD_SIZE, FormatError, status_values)

class PlotBuckets:
    """Keep min/max points per bucket, not every high-rate sample."""
    def __init__(self, stride):
        self.stride = max(1, stride)
        self.points = []
        self.pending = []
    def add(self, t, value):
        self.pending.append((t, value))
        if len(self.pending) >= self.stride:
            self.flush()
    def flush(self):
        if self.pending:
            self.points.extend(sorted((min(self.pending, key=lambda p:p[1]),
                                       max(self.pending, key=lambda p:p[1]))))
            self.pending.clear()

def plots(output, channels, synthetic):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), constrained_layout=True)
    for index, names in enumerate((tuple(n for n in channels if n.startswith('emg')), ('foot_ax','foot_ay','foot_az'),
                                   ('shank_ax','shank_ay','shank_az'))):
        for name in names:
            series = channels[name];series.flush()
            if series.points:
                x,y = zip(*series.points);axes[index].plot(x,y,label=name,linewidth=.6)
        axes[index].legend(loc='upper right');axes[index].grid(alpha=.25)
        axes[index].set_ylabel('ADC output (V)' if index==0 else 'Acceleration (g)')
        axes[index].set_xlabel('ESP32 boot time (s)' if index==0 else 'Estimated ESP32 time (s); IMU delay uncorrected')
    fig.suptitle(('SYNTHETIC DEMONSTRATION — ' if synthetic else '')+'Raw acquisition diagnostics; min/max display reduction')
    fig.savefig(output/'signals.png',dpi=160)
    fig.savefig(output/'signals.svg')
    plt.close(fig)

def convert(source: Path, output: Path, *, recover=False, make_plots=True, operator_metadata=None):
    source=Path(source);output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('output directory must be empty; existing results will not be overwritten')
    # Validate metadata before creating any export files.
    with source.open('rb') as f:
        metadata=read_header(f)
    output.mkdir(parents=True,exist_ok=True)
    issues=[];counts={name:0 for name in KINDS.values()};last_seq={};last_time={}
    sequence_gaps={name:0 for name in ('emg','foot','shank')}
    anomalies={name:0 for name in ('sequence_regressions','timestamp_regressions',
        'emg_clipped_samples','emg_out_of_range','imu_invalid_samples',
        'imu_timestamp_anomalies','timing_uncertain_records','flagged_gap_records')}
    total_slots=0;observed_missed=0;first_emg=None;last_emg=None;last_end=None;end_seen=False
    sensor_last={};sensor_unwrapped={};last_status=None
    records_est=max(1,(source.stat().st_size-HEADER_SIZE)//RECORD_SIZE)
    revb=metadata['schema']!='afo-recorder/1'
    ad7606=metadata['schema']=='afo-recorder/3'
    limit=1<<(metadata['adc_bits']-1)
    count=metadata.get('active_channel_count',2)
    channels={f'emg{i}':PlotBuckets(max(1,records_est//2000)) for i in range(count)}
    channels.update({f'{body}_{axis}':PlotBuckets(max(1,int(records_est*metadata['imu_hz']/metadata['emg_hz'])//2000))
                     for body in ('foot','shank') for axis in ('ax','ay','az')})
    try:
        with ExitStack() as stack:
            stream=stack.enter_context(source.open('rb'));read_header(stream)
            writers={}
            columns={
                'emg':['sequence','ch0_transaction_start_us','ch0_raw','ch1_raw','ch0_voltage','ch1_voltage',
                       'ch0_transaction_us','ch1_transaction_start_us','ch1_transaction_us','elapsed_slots','flags'],
                'foot':['sequence','host_time_estimate_us','sensor_time_unwrapped_us','sensor_timestamp_raw',
                        'ax_raw','ay_raw','az_raw','gx_raw','gy_raw','gz_raw','ax_g','ay_g','az_g',
                        'gx_dps','gy_dps','gz_dps','temperature_raw','fifo_header','read_start_us','read_end_us','irq_anchor_us','flags','valid'],
                'status':['kind','sequence','timestamp_us','flags','timer_missed','queue_dropped','imu_errors',
                          'fifo_overflows','adc_errors','emg_records','foot_records','shank_records','battery_mv','queue_high_water']}
            if revb:
                columns['emg']=['sequence','conversion_trigger_host_us' if ad7606 else 'adc_drdy_host_us']+[f'ch{i}_raw' for i in range(count)]+[f'ch{i}_adc_input_v' if ad7606 else f'ch{i}_differential_v' for i in range(count)]+[f'ch{i}_myoware_raw_v_estimate' for i in range(count)]+['adc_status','adc_crc','read_start_us','read_duration_us','elapsed_slots','active_mask','flags']
            columns['shank']=columns['foot']
            for name,cols in columns.items():
                f=stack.enter_context((output/f'{name}.csv').open('w',newline=''))
                writers[name]=csv.writer(f);writers[name].writerow(cols)
            for rec in iter_records(stream,recover,issues):
                name=KINDS[rec.kind];counts[name]+=1
                if end_seen:
                    raise FormatError('records found after session END; file may contain concatenated sessions')
                if rec.kind in (1,2,3,6,7):
                    prev=last_seq.get(name,0)
                    if rec.sequence<=prev:anomalies['sequence_regressions']+=1
                    else:sequence_gaps[name]+=rec.sequence-prev-1
                    if name in last_time and rec.timestamp_us<=last_time[name]:anomalies['timestamp_regressions']+=1
                    last_seq[name]=rec.sequence;last_time[name]=rec.timestamp_us
                    if rec.flags&2:anomalies['timing_uncertain_records']+=1
                    if rec.flags&1:anomalies['flagged_gap_records']+=1
                if rec.kind in (6,7):
                    values,status,crc,duration,slots,start=decode_emg_b(rec,metadata)
                    total_slots+=slots;observed_missed+=max(0,slots-1)
                    anomalies['emg_clipped_samples']+=sum(v in (-limit,limit-1) for v in values)
                    if rec.flags&4 or status&0x5400:anomalies['emg_out_of_range']+=1
                    scale=metadata['adc_reference_mv']/1000/limit
                    volts=[v*scale for v in values]
                    estimates=[v/metadata['input_scale']+metadata['input_midpoint_mv']/1000 for v in volts]
                    writers['emg'].writerow([rec.sequence,rec.timestamp_us,*values,*volts,*estimates,"" if ad7606 else status,"" if ad7606 else crc,start,duration,slots,(1<<count)-1,rec.flags])
                    for i,v in enumerate(volts):channels[f'emg{i}'].add(rec.timestamp_us/1e6,v)
                    if first_emg is None:first_emg=(rec.sequence,rec.timestamp_us)
                    last_emg=(rec.sequence,rec.timestamp_us)
                elif rec.kind==1:
                    if revb:raise FormatError('Legacy EMG frame in Rev B session')
                    a,b,d0,offset,d1,slots=EMG.unpack(rec.payload)
                    total_slots+=slots;observed_missed+=max(0,slots-1)
                    anomalies['emg_out_of_range']+=int(a>4095)+int(b>4095)
                    anomalies['emg_clipped_samples']+=int(a in (0,4095))+int(b in (0,4095))
                    if slots<1:raise FormatError('EMG elapsed_slots must be positive')
                    scale=metadata['adc_reference_mv']/1000/4096
                    writers['emg'].writerow([rec.sequence,rec.timestamp_us,a,b,a*scale,b*scale,d0,
                                            rec.timestamp_us+offset,d1,slots,rec.flags])
                    channels['emg0'].add(rec.timestamp_us/1e6,a*scale)
                    channels['emg1'].add((rec.timestamp_us+offset)/1e6,b*scale)
                    if first_emg is None:first_emg=(rec.sequence,rec.timestamp_us)
                    last_emg=(rec.sequence,rec.timestamp_us)
                elif rec.kind in (2,3):
                    packet,read_start,read_end,anchor=IMU.unpack(rec.payload);p=decode_fifo(packet)
                    raw=p['sensor_timestamp_raw']
                    if name in sensor_last:
                        delta=(raw-sensor_last[name])&0xffff
                        nominal=1e6/metadata['imu_hz']
                        if not .8*nominal<=delta<=1.2*nominal:anomalies['imu_timestamp_anomalies']+=1
                        sensor_unwrapped[name]+=delta
                    else:sensor_unwrapped[name]=raw
                    sensor_last[name]=raw
                    axes=[p[k] for k in ('ax','ay','az','gx','gy','gz')]
                    scaled=[v*metadata['accel_range_g']/32768 for v in axes[:3]]+[
                            v*metadata['gyro_range_dps']/32768 for v in axes[3:]]
                    valid=p['valid'] and not rec.flags&4
                    if not valid:anomalies['imu_invalid_samples']+=1
                    writers[name].writerow([rec.sequence,rec.timestamp_us,sensor_unwrapped[name],raw,
                        *axes,*scaled,p['temperature_raw'],p['header'],read_start,read_end,anchor,rec.flags,int(valid)])
                    if valid:
                        for axis,value in zip(('ax','ay','az'),scaled):channels[f'{name}_{axis}'].add(rec.timestamp_us/1e6,value)
                else:
                    values=status_values(rec.payload);last_status=values
                    writers['status'].writerow([name,rec.sequence,rec.timestamp_us,rec.flags,*values.values()])
                    if rec.kind==5:last_end=rec;end_seen=True
    except (FormatError, OSError) as exc:
        (output/'CONVERSION_FAILED.txt').write_text(str(exc)+'\nPartial CSV files are not a validated export.\n')
        raise
    if not end_seen:issues.append({'kind':'missing_end','message':'Unfinalized session; trailing samples may be lost.'})
    for name in (('emg','foot','shank') if metadata.get('imu_enabled',True) else ('emg',)):
        if counts[name]==0:issues.append({'kind':'missing_stream','stream':name})
    if last_status:
        for name in ('emg','foot','shank'):
            if last_status[f'{name}_records']!=counts[name]:
                issues.append({'kind':'counter_mismatch','stream':name,'reported':last_status[f'{name}_records'],'decoded':counts[name]})
    if last_end and last_end.flags!=0:issues.append({'kind':'abnormal_stop','reason':last_end.flags})
    rate=None
    if first_emg and last_emg and last_emg[1]>first_emg[1]:
        rate=(last_emg[0]-first_emg[0])*1e6/(last_emg[1]-first_emg[1])
    counters_clean=last_status is not None and all(last_status[k]==0 for k in (
        'timer_missed','queue_dropped','imu_errors','fifo_overflows','adc_errors'))
    structurally_complete=end_seen and not issues
    no_loss=structurally_complete and counters_clean and not any(sequence_gaps.values()) and observed_missed==0
    signal_valid=not any(anomalies[k] for k in ('sequence_regressions','timestamp_regressions',
        'emg_clipped_samples','emg_out_of_range','imu_invalid_samples','imu_timestamp_anomalies','flagged_gap_records'))
    with source.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    report={'source_sha256':digest,'synthetic':metadata.get('synthetic',False),'counts':counts,
            'session_finalized':end_seen,'structurally_complete':structurally_complete,
            'no_detected_sample_loss':no_loss,'signal_checks_pass':signal_valid,
            'research_ready':False,'sequence_gaps':sequence_gaps,'anomalies':anomalies,
            'emg_observed_skipped_slots':observed_missed,'emg_rate_from_host_timestamps_hz':rate,
            'last_status':last_status,'issues':issues,
            'timing_note':'IMU host timestamps are estimates. Internal clock drift and sensor/analog filter delays are uncorrected.',
            'recovery_note':'Timestamp unwrapping is ambiguous across long gaps; never infer missing cycles after corruption.'}
    (output/'metadata.json').write_text(json.dumps({'recorded':metadata,'operator_metadata':operator_metadata or {}},indent=2)+'\n')
    (output/'quality.json').write_text(json.dumps(report,indent=2)+'\n')
    if make_plots:plots(output,channels,metadata.get('synthetic',False))
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--recover',action='store_true',help='Salvage CRC-valid records and explicitly report gaps')
    parser.add_argument('--no-plots',action='store_true')
    parser.add_argument('--operator-metadata',type=Path,help='JSON with pseudonymous trial label, placement and calibration notes')
    args=parser.parse_args()
    try:
        notes=json.loads(args.operator_metadata.read_text()) if args.operator_metadata else None
        if notes is not None and not isinstance(notes,dict):raise ValueError('operator metadata must be a JSON object')
        report=convert(args.source,args.out,recover=args.recover,make_plots=not args.no_plots,operator_metadata=notes)
    except (ValueError,OSError,ImportError) as exc:
        print(f'Conversion failed: {exc}',file=sys.stderr);return 1
    print(json.dumps({k:report[k] for k in ('counts','session_finalized','no_detected_sample_loss','signal_checks_pass')},indent=2))
    return 0 if report['no_detected_sample_loss'] and report['signal_checks_pass'] else 2

if __name__=='__main__':raise SystemExit(main())
