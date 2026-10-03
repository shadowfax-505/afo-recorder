#!/usr/bin/env python3
"""Independently compare actual Wokwi file bytes, CSV exports and test inputs.

Uses only the Python standard library. Does not import the recorder converter,
regenerate recordings, infer missing samples, or qualify physical measurements.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

P = Path(__file__).resolve().parent
KINDS = {7: 'emg', 2: 'foot', 3: 'shank', 4: 'status', 5: 'end'}
STATUS_KEYS = ['timer_missed', 'queue_dropped', 'imu_errors', 'fifo_overflows',
               'adc_errors', 'emg_records', 'foot_records', 'shank_records',
               'battery_mv', 'queue_high_water']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_binary(path):
    data = Path(path).read_bytes()
    require(len(data) >= 4096, 'Truncated 4096-byte header')
    require((len(data) - 4096) % 64 == 0, 'Truncated 64-byte record')
    magic, version, size, length = struct.unpack_from('<8sHHI', data)
    require((magic, version, size) == (b'AFOLOG1\0', 1, 4096), 'Wrong file signature')
    require(length <= 4076, 'Metadata exceeds header')
    require(zlib.crc32(data[:4092]) == struct.unpack_from('<I', data, 4092)[0], 'Header CRC32')
    meta = json.loads(data[16:16 + length])
    records = []
    for offset in range(4096, len(data), 64):
        block = data[offset:offset + 64]
        magic, kind, flags, length, sequence, stamp, payload, crc = struct.unpack('<4sBBHIQ40sI', block)
        require(magic == b'AFR1' and kind in KINDS and length == 40, f'Type/length at {offset}')
        require(zlib.crc32(block[:60]) == crc, f'Record CRC32 at {offset}')
        records.append(dict(kind=kind, flags=flags, sequence=sequence, stamp=stamp,
                            payload=payload, block=block))
    return data, meta, records


def read_csv(path):
    with Path(path).open(newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames, rows


def equal(row, field, value):
    actual = row[field]
    if isinstance(value, float):
        require(math.isfinite(float(actual)) and abs(float(actual) - value) <= 1e-12,
                f'CSV scaling/value differs: {field}')
    else:
        require(actual == str(value), f'CSV value differs: {field}')


def audit_case(folder, stimulus=None):
    folder = Path(folder)
    raw, original, records = read_binary(folder / 'recorder-output.raw')
    tagged, meta, tagged_records = read_binary(folder / 'simulated-recording.afolog')
    require(raw[4096:] == tagged[4096:], 'Simulation tagging changed original records')
    changes = {k for k in original.keys() | meta.keys() if original.get(k) != meta.get(k)}
    require(changes == {'synthetic', 'simulation'} and meta['synthetic'] is True,
            'Unexpected change to simulation provenance header')
    require(original['synthetic'] is False, 'Original firmware header changed')
    expected = dict(schema='afo-recorder/3', adc_model='AD7606', adc_bits=16,
                    active_channel_count=2, emg_channels=['EMG1', 'EMG2'],
                    adc_reference_mv=5000, input_scale=1, input_midpoint_mv=0,
                    adc_sensor_crc_supported=False, emg_hz=8000, imu_hz=200,
                    accel_range_g=16, gyro_range_dps=2000,
                    calibration_state='uncalibrated', imu_timing_calibrated=False)
    require(all(meta.get(k) == v for k, v in expected.items()), 'Configuration/units mismatch')
    exported = json.loads((folder / 'converted/metadata.json').read_text())['recorded']
    require(exported == meta, 'Exported metadata differs from binary header')
    quality = json.loads((folder / 'converted/quality.json').read_text())
    counts = dict(collections.Counter(KINDS[r['kind']] for r in records))
    require(counts == dict(emg=10041, foot=263, shank=252, status=1, end=1), 'Unexpected nominal record counts')
    require(quality['counts'] == counts and quality['source_sha256'] == hashlib.sha256(tagged).hexdigest(),
            'Quality source/counts do not identify this recording')
    require(all(quality[k] is True for k in ['session_finalized', 'structurally_complete',
                                           'no_detected_sample_loss', 'signal_checks_pass']), 'Nominal quality flags')
    require(quality['research_ready'] is False and quality['synthetic'] is True,
            'Simulation incorrectly presented as research-ready measurements')
    require(records[-1]['kind'] == 5 and records[-1]['flags'] == 0 and
            sum(r['kind'] == 5 for r in records) == 1, 'Missing/duplicate/nonfinal END')
    grouped = {name: [r for r in records if KINDS[r['kind']] == name] for name in counts}
    for name in ['emg', 'foot', 'shank']:
        rr = grouped[name]
        require([r['sequence'] for r in rr] == list(range(1, len(rr) + 1)), f'{name} sequence gap')
        require(all(b['stamp'] > a['stamp'] for a, b in zip(rr, rr[1:])), f'{name} timestamp regression')
    inputs = None
    if stimulus is not None:
        _, inputs = read_csv(stimulus)
        require(len(inputs) == 8000, 'Expected one-second, 8000-sample stimulus')
    header, rows = read_csv(folder / 'converted/emg.csv')
    expected_columns = ['sequence', 'conversion_trigger_host_us', 'ch0_raw', 'ch1_raw',
                        'ch0_adc_input_v', 'ch1_adc_input_v', 'ch0_myoware_raw_v_estimate',
                        'ch1_myoware_raw_v_estimate', 'adc_status', 'adc_crc', 'read_start_us',
                        'read_duration_us', 'elapsed_slots', 'active_mask', 'flags']
    require(header == expected_columns and len(rows) == counts['emg'], 'EMG CSV columns/count')
    max_quantization_error = 0.
    for i, (rec, row) in enumerate(zip(grouped['emg'], rows)):
        a, b, c, d, status, adc_crc, duration, slots, mask, start = struct.unpack('<4iHHIIB3xQ', rec['payload'])
        want = [int(inputs[i % 8000]['code1']), int(inputs[i % 8000]['code2'])] if inputs else [6554, 13107]
        require([a, b] == want, f'Stimulus/channel identity mismatch at EMG frame {i + 1}')
        require(c == d == status == adc_crc == 0 and slots == 1 and mask == 3 and rec['flags'] == 0,
                'Disabled channel data, wrong channel mask, unsupported ADC CRC/status or missed slot')
        require(start >= rec['stamp'] and duration > 0, 'Invalid ADC read timing')
        values = dict(sequence=rec['sequence'], conversion_trigger_host_us=rec['stamp'],
                      ch0_raw=a, ch1_raw=b, read_start_us=start, read_duration_us=duration,
                      elapsed_slots=slots, active_mask=mask, flags=rec['flags'], adc_status='', adc_crc='')
        for ch, value in enumerate([a, b]):
            voltage = value * 5 / 32768
            values[f'ch{ch}_adc_input_v'] = voltage
            values[f'ch{ch}_myoware_raw_v_estimate'] = voltage
            if inputs:
                max_quantization_error = max(max_quantization_error,
                    abs(voltage - float(inputs[i % 8000][f'emg{ch + 1}_v'])))
        for field, value in values.items(): equal(row, field, value)
    require(max_quantization_error <= 5 / 65536 + 1e-12, 'Quantization exceeds half nominal LSB')
    imu_results = {}
    for name, marker in [('foot', 1), ('shank', 2)]:
        _, rows = read_csv(folder / f'converted/{name}.csv')
        require(len(rows) == counts[name], f'{name} CSV count')
        unwrap = 0; previous = None; rollovers = 0; samples_after_read_start = 0; samples_after_irq_anchor = 0
        for rec, row in zip(grouped[name], rows):
            packet, start, end, anchor = struct.unpack('<16sQQQ', rec['payload'])
            header, ax, ay, az, gx, gy, gz, temperature, tick = struct.unpack('>B6hbH', packet)
            require(header == 104 and [ax, ay, az, gx, gy, gz] == [marker, 0, 2048, 0, 0, 0],
                    f'{name} FIFO axis order/sensor identity')
            if previous is None: unwrap = tick
            else:
                require((tick - previous) & 65535 == 5000, f'{name} sensor time interval')
                rollovers += tick < previous
                unwrap += 5000
            previous = tick
            # The same read interval/IRQ anchor belongs to a FIFO burst. Later
            # packets can be produced during that read or after its first IRQ.
            # Do not mistake a burst-start time for every packet's sample time.
            require(rec['flags'] == 2 and end >= start and rec['stamp'] <= end and anchor <= end,
                    f'{name} uncertain timing flag/read timing missing')
            samples_after_read_start += rec['stamp'] > start
            samples_after_irq_anchor += rec['stamp'] > anchor
            values = dict(sequence=rec['sequence'], host_time_estimate_us=rec['stamp'],
                          sensor_time_unwrapped_us=unwrap, sensor_timestamp_raw=tick,
                          ax_raw=ax, ay_raw=ay, az_raw=az, gx_raw=gx, gy_raw=gy, gz_raw=gz,
                          ax_g=ax / 2048, ay_g=ay / 2048, az_g=az / 2048,
                          gx_dps=gx * 2000 / 32768, gy_dps=gy * 2000 / 32768, gz_dps=gz * 2000 / 32768,
                          temperature_raw=temperature, fifo_header=header,
                          read_start_us=start, read_end_us=end, irq_anchor_us=anchor, flags=2, valid=1)
            for field, value in values.items(): equal(row, field, value)
        imu_results[name] = dict(rows=len(rows), counter_rollovers=rollovers,
            first_host_estimate_us=grouped[name][0]['stamp'], last_host_estimate_us=grouped[name][-1]['stamp'],
            nominal_sensor_interval_us=5000, timing_uncertain_records=len(rows), stationary_z_g=1.,
            samples_after_burst_read_start=samples_after_read_start,
            samples_after_burst_irq_anchor=samples_after_irq_anchor)
    _, statuses = read_csv(folder / 'converted/status.csv')
    require(len(statuses) == 2, 'Status CSV count')
    for rec, row in zip([r for r in records if r['kind'] in (4, 5)], statuses):
        values = dict(zip(STATUS_KEYS, struct.unpack('<10I', rec['payload'])))
        for k, v in dict(kind=KINDS[rec['kind']], sequence=rec['sequence'], timestamp_us=rec['stamp'],
                         flags=rec['flags'], **values).items(): equal(row, k, v)
    require(all(values[k] == 0 for k in STATUS_KEYS[:5]) and
            all(values[f'{n}_records'] == counts[n] for n in ['emg', 'foot', 'shank']), 'Final counters disagree')
    require(values == quality['last_status'], 'Quality report final counters differ')
    live = json.loads((folder / 'live-results.json').read_text())
    require(live['ended'] and live['stop_reason'] == 0 and live['records'] == len(records) - 1,
            'Unexpected live output coverage')
    require(live['stats']['device_queue_drops'] == 1 and live['sequence_gaps'] == {'7': 1},
            'Wireless-only missing frame was hidden')
    live_files = list((folder / 'live-capture').glob('*.afolog'))
    require(len(live_files) == 1, 'Ambiguous live archive')
    _, _, preview = read_binary(live_files[0])
    saved = {(r['kind'], r['sequence']): r['block'] for r in records}
    keys = [(r['kind'], r['sequence']) for r in preview]
    require(len(set(keys)) == len(keys) and all(saved.get(k) == r['block'] for k, r in zip(keys, preview)),
            'Live record differs from authoritative saved bytes')
    missing = sorted(saved.keys() - set(keys))
    require(len(missing) == 1 and missing[0][0] == 7, 'Unexpected live-only missing record')
    emg = grouped['emg']
    return dict(passed=True, hardware_measured=False, synthetic=True,
                original_sha256=hashlib.sha256(raw).hexdigest(),
                tagged_sha256=hashlib.sha256(tagged).hexdigest(), bytes=len(raw), record_bytes=64,
                header_bytes=4096, validated_record_crc32=len(records), counts=counts,
                header_changes=sorted(changes), record_body_unchanged=True,
                csv_rows_compared=sum(counts.values()), emg_values_compared=2 * counts['emg'],
                channel_mapping={'ch0': 'EMG1', 'ch1': 'EMG2'}, unused_channels_exported=False,
                expected_emg_input='Precomputed ngspice synthetic stimulus' if inputs else 'Known nominal 1 V / 2 V codes',
                nominal_lsb_v=5 / 32768, max_quantization_error_v=max_quantization_error if inputs else None,
                first_emg_host_us=emg[0]['stamp'], last_emg_host_us=emg[-1]['stamp'],
                host_span_s=(emg[-1]['stamp'] - emg[0]['stamp']) / 1e6,
                host_rate_hz=(len(emg) - 1) * 1e6 / (emg[-1]['stamp'] - emg[0]['stamp']),
                imu=imu_results, saved_sequence_gaps=0, live_missing_emg_sequence=missing[0][1],
                live_records_identical_to_saved=True, timing_calibrated=False, research_ready=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--examples', type=Path, help='Use extracted download examples instead of repository sources')
    parser.add_argument('--output', type=Path, default=P / 'results.json')
    args = parser.parse_args()
    if args.examples:
        base = args.examples
        normal, wave, stimulus = base / 'known-dc', base / 'synthetic-waveform', base / 'filtered-samples.csv'
    else:
        integrated = P.parent / 'integrated-recorder'
        normal = integrated / 'full-system/trace-validation/probe-run'
        wave = integrated / 'results/web-current/filtered-synthetic-emg'
        stimulus = integrated / 'stimulus/filtered-samples.csv'
    report = dict(passed=True, method='Independent stdlib byte/CRC/CSV/input comparison',
                  hardware_measured=False, cases={'known-dc': audit_case(normal),
                                                'synthetic-waveform': audit_case(wave, stimulus)})
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': True, 'cases': 2, 'record_crc32_checks': sum(v['validated_record_crc32'] for v in report['cases'].values()),
                      'csv_rows_compared': sum(v['csv_rows_compared'] for v in report['cases'].values())}))


if __name__ == '__main__': main()
