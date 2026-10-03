#!/usr/bin/env python3
"""Make named, relative-time analysis tables from a validated converter export.

No interpolation, centering, smoothing or EMG normalization is performed.
The source metadata and quality report remain the authority for interpretation.
"""
import argparse
import csv
import json
from pathlib import Path


def read_rows(path):
    with path.open(newline='') as f: return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('converted', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    meta = json.loads((args.converted / 'metadata.json').read_text())['recorded']
    quality = json.loads((args.converted / 'quality.json').read_text())
    if meta.get('schema') != 'afo-recorder/3' or meta.get('active_channel_count') != 2:
        raise ValueError('This example supports the selected AD7606 / two-channel format')
    if not quality.get('structurally_complete') or not quality.get('no_detected_sample_loss'):
        raise ValueError('Inspect gaps or incomplete recording before using this simple example')
    emg = read_rows(args.converted / 'emg.csv')
    if not emg: raise ValueError('No EMG rows')
    if args.output.exists(): raise ValueError('Choose a new output folder; existing results are preserved')
    args.output.mkdir(parents=True)
    origin = int(emg[0]['conversion_trigger_host_us'])
    with (args.output / 'muscle.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['sequence', 'time_since_first_emg_s', 'EMG1_adc_input_V', 'EMG2_adc_input_V', 'flags'])
        for r in emg:
            writer.writerow([r['sequence'], (int(r['conversion_trigger_host_us']) - origin) / 1e6,
                             r['ch0_adc_input_v'], r['ch1_adc_input_v'], r['flags']])
    for body in ['foot', 'shank']:
        rows = read_rows(args.converted / f'{body}.csv')
        with (args.output / f'{body}-motion.csv').open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['sequence', 'estimated_time_since_first_emg_s', 'sensor_time_unwrapped_us',
                             'ax_g', 'ay_g', 'az_g', 'gx_deg_per_s', 'gy_deg_per_s', 'gz_deg_per_s', 'flags', 'valid'])
            for r in rows:
                writer.writerow([r['sequence'], (int(r['host_time_estimate_us']) - origin) / 1e6,
                                 r['sensor_time_unwrapped_us'], *[r[k] for k in
                                    ['ax_g', 'ay_g', 'az_g', 'gx_dps', 'gy_dps', 'gz_dps']], r['flags'], r['valid']])
    (args.output / 'interpretation.json').write_text(json.dumps(dict(
        source_sha256=quality['source_sha256'], synthetic=meta.get('synthetic', False),
        time_origin_host_us=origin, time_origin='first saved EMG CONVST software timestamp',
        channel_identities=meta['emg_channels'], calibration_state=meta['calibration_state'],
        no_resampling=True, no_filtering=True, no_missing_samples_inferred=True,
        imu_times_estimated=True, imu_timing_calibrated=meta['imu_timing_calibrated'],
        research_ready=False, note='Voltage is ADC input, not muscle input microvolts. Negative initial foot time is retained.'
    ), indent=2) + '\n')
    print(json.dumps({'emg_rows': len(emg), 'output': str(args.output)}))


if __name__ == '__main__': main()
