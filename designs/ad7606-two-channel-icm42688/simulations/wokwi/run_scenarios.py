#!/usr/bin/env python3
"""Run actual ESP32 firmware; fresh evidence is required for every scenario."""
import json
import os
import re
import subprocess
import tempfile
from verify_trace import verify
from pathlib import Path

P = Path(__file__).resolve().parent
EXPECTED = {
    'normal': 'WINDOW_COMPLETE',
    'stuck-busy': 'FAIL,ADC BUSY edge timeout',
    'delayed-busy': 'FAIL,ADC late conversion/read',
    'incorrect-mode': 'codes differ from known stimulus',
    'absent-shank': 'FAIL,IMU init/identity/readback',
    'fifo-overflow': 'FAIL,IMU FIFO/read',
    'missed-interrupt': 'FAIL,IMU missing interrupts/data',
}


def assess(name, text):
    """Check complete diagnostic lines, never a mean or marker in isolation."""
    failures = re.findall(r'^FAIL,([^\r\n]+)', text, re.M)
    if name not in ('normal', 'incorrect-mode'):
        expected = EXPECTED[name][5:]
        return bool(failures) and all(f.startswith(expected + ',') for f in failures)
    if failures:
        return False
    pattern = (r'^ADC,elapsed_us=(\d+),edges=(\d+),good=(\d+)'
               r',ch1_mean=([-\d.]+),min=(-?\d+),max=(-?\d+),rms_ac_codes=([\d.]+)'
               r',ch2_mean=([-\d.]+),min=(-?\d+),max=(-?\d+),rms_ac_codes=([\d.]+)$')
    frames = re.findall(pattern, text, re.M)
    if not frames or text.count('WINDOW_COMPLETE;') != len(frames):
        return False
    for frame in frames:
        elapsed, edges, good = map(int, frame[:3])
        # Integration gate, not a claim of real hardware jitter or endurance.
        if not 990000 <= elapsed <= 1010000 or edges != good:
            return False
        if not 7920 <= good * 1000000 / elapsed <= 8080:
            return False
        for offset, code in ((3, 6554), (7, 13107)):
            mean, low, high, rms = map(float, frame[offset:offset + 4])
            target = code if name == 'normal' else -1  # all-ones wrong-mode model
            if abs(mean - target) > .01 or low != target or high != target or rms != 0:
                return False
    for sensor in (0, 1):
        imu = re.findall(rf'^IMU,{sensor},packets=(\d+),interrupts=(\d+),'
                         rf'ax_raw={sensor + 1},ay_raw=0,az_raw=2048,'
                         r'gx_raw=0,gy_raw=0,gz_raw=0,timestamp_raw=(\d+)$', text, re.M)
        if len(imu) != len(frames):
            return False
        if any(not (195 <= int(p) <= 205 and 195 <= int(i) <= 205 and int(t) <= 65535)
               for p, i, t in imu):
            return False
    return True


def trace_has_activity(path):
    """Reject empty/header-only traces. Full protocol trace review is separate."""
    if not path.is_file():
        return False
    text = path.read_text(errors='replace')
    if '$enddefinitions' not in text or '$timescale' not in text:
        return False
    ids = set(re.findall(r'\$var\s+\S+\s+1\s+(\S+)\s+', text))
    last, time, changed = {}, 0, set()
    for line in text.split('$enddefinitions', 1)[1].splitlines():
        line = line.strip()
        if re.fullmatch(r'#\d+', line):
            time = int(line[1:])
        elif line[:1] in ('0', '1') and line[1:] in ids:
            key, value = line[1:], line[0]
            if time > 0 and key in last and last[key] != value:
                changed.add(key)
            last[key] = value
    return bool(changed)


def run_case(name, out, execute=subprocess.run):
    serial, vcd = out / f'{name}.serial.txt', out / f'{name}.vcd'
    # Also make direct/retried calls safe if the caller reuses a directory.
    serial.unlink(missing_ok=True)
    vcd.unlink(missing_ok=True)
    cmd = [os.environ.get('WOKWI_CLI', 'wokwi-cli'), str(P), '--diagram-file',
           str(P / 'scenarios' / f'{name}.json'), '--timeout', '2500',
           '--timeout-exit-code', '0', '--serial-log-file', str(serial), '--vcd-file', str(vcd)]
    result = {'case': name, 'expected': EXPECTED[name], 'pass': False}
    try:
        process = execute(cmd, capture_output=True, text=True, timeout=180)
        (out / f'{name}.cli.txt').write_text(process.stdout + process.stderr)
        text = serial.read_text() if serial.exists() else ''
        result.update(exit_code=process.returncode, serial_pass=assess(name, text),
                      trace_activity=trace_has_activity(vcd))
        if result['trace_activity']:
            trace = verify(vcd, name)
            (out / f'{name}.trace.json').write_text(json.dumps(trace, indent=2) + '\n')
            result['trace_protocol_pass'] = trace['pass']
        else:
            result['trace_protocol_pass'] = False
        result['pass'] = process.returncode == 0 and result['serial_pass'] and result['trace_protocol_pass']
    except (subprocess.TimeoutExpired, OSError) as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    return result


def main():
    if not os.environ.get('WOKWI_CLI_TOKEN'):
        raise SystemExit('WOKWI_CLI_TOKEN is not configured. No simulation pass is claimed. '
                         'Configure it locally; do not commit it.')
    root = P / 'results'
    root.mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='run-', dir=root))
    results = []
    for name in EXPECTED:
        print('Running ' + name, flush=True)
        result = run_case(name, out)
        results.append(result)
        print(json.dumps(result), flush=True)
    (out / 'scenarios.json').write_text(json.dumps({
        'engine': 'Wokwi ESP32-S3', 'hardware_measured': False,
        'trace_check': '128-clock frames, signed word order, conversion/BUSY timing and fault signatures',
        'cases': results}, indent=2) + '\n')
    print(out)
    return 0 if all(case['pass'] for case in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
