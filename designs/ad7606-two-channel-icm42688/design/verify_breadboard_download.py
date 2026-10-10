#!/usr/bin/env python3
"""Extract the actual lab ZIP and verify its laptop tools outside the repository."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import zipfile

VARIANT = Path(__file__).resolve().parents[1]
PROBE = VARIANT / 'simulations/integrated-recorder/full-system/trace-validation/probe-run'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(python, kit, args, log, expected_exit=0):
    env = os.environ.copy()
    for key in ['PYTHONPATH', 'PYTHONHOME']:
        env.pop(key, None)
    result = subprocess.run([str(python), '-s', *map(str, args)], cwd=kit, env=env,
                            text=True, capture_output=True, timeout=120)
    log.write_text(result.stdout + result.stderr)
    if result.returncode != expected_exit:
        raise AssertionError(f'{args[0]} returned {result.returncode}; see {log.name}')
    return result


def fetch(url):
    with urlopen(url, timeout=2) as response:
        return response.read()


def wait_snapshot(url, test, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = json.loads(fetch(url + 'api'))
        if test(snapshot):
            return snapshot
        time.sleep(.02)
    raise TimeoutError('Receiver API did not reach the expected state')


def replay(python, kit, out):
    # Only the extracted kit supplies the protocol decoder. This runner supplies
    # a frozen captured input stream, not a regenerated ADC/IMU behavior model.
    sys.path.insert(0, str(kit / 'host'))
    from afo_format import decode_record
    from live_protocol import decode_packet, encode_packet

    source = (PROBE / 'udp-output.raw').read_bytes()
    packets = []
    at = 0
    while at < len(source):
        size, = struct.unpack_from('<H', source, at)
        at += 2
        packet = source[at:at + size]
        if len(packet) != size:
            raise ValueError('Truncated frozen UDP packet')
        at += size
        decoded = decode_packet(packet)
        if decoded['kind'] == 1:
            # Keep captured measurement bytes unchanged; tag metadata as synthetic.
            metadata = dict(decoded['metadata'], synthetic=True)
            packet = encode_packet(1, decoded['boot'], decoded['session'], decoded['sequence'],
                                   json.dumps(metadata, separators=(',', ':')).encode(),
                                   dropped=decoded['dropped'])
        packets.append(packet)
    expected = json.loads((PROBE / 'live-results.json').read_text())
    body = b''.join(decode_packet(packet)['payload'] for packet in packets
                    if decode_packet(packet)['kind'] == 2)
    capture = out / 'laptop-capture'
    console = out / 'receiver-console.txt'
    env = os.environ.copy()
    for key in ['PYTHONPATH', 'PYTHONHOME']:
        env.pop(key, None)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as device, console.open('w') as log:
        device.bind(('127.0.0.1', 0))
        device.settimeout(5)
        process = subprocess.Popen([str(python), '-s', str(kit / 'host/live_receiver.py'),
                                    '--device', '127.0.0.1', '--udp-port', str(device.getsockname()[1]),
                                    '--http-port', '0', '--out', str(capture), '--no-browser'],
                                   cwd=kit, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            hello, peer = device.recvfrom(2048)
            assert hello == b'AFO-LIVE1'
            url = None
            deadline = time.monotonic() + 5
            while url is None and time.monotonic() < deadline:
                url = next((line.split(': ', 1)[1] for line in console.read_text().splitlines()
                            if line.startswith('Live viewer: ')), None)
                if url is None:
                    time.sleep(.02)
            if url is None:
                raise TimeoutError('Receiver did not announce its local viewer URL')
            assert fetch(url) == (kit / 'host/live_view.html').read_bytes()
            for packet in packets:
                device.sendto(packet, peer)
                time.sleep(.001)  # Pace loopback replay; do not create additional kernel loss.
            snapshot = wait_snapshot(url, lambda value: value.get('records') == expected['records'])
            assert snapshot['stats'] == expected['stats']
            for key in ['sequence_gaps', 'imu', 'health', 'ended', 'stop_reason']:
                assert snapshot[key] == expected[key], key
            assert snapshot['metadata']['synthetic'] is True
            assert snapshot['metadata']['emg_channels'] == ['EMG1', 'EMG2']
            assert all(len(row) == 5 for row in snapshot['emg'])
            assert len(snapshot['emg']) == 800
            for row in snapshot['emg']:
                assert abs(row[1] - 6554 * 5 / 32768) < 1e-12
                assert abs(row[2] - 13107 * 5 / 32768) < 1e-12
            bad = bytearray(packets[-1])
            bad[-1] ^= 1
            device.sendto(bad, peer)
            device.sendto(packets[-1], peer)
            after = wait_snapshot(url, lambda value: value['stats']['invalid_packets'] == 1
                                  and value['stats']['reordered_or_duplicate'] == 1)
            assert after['records'] == snapshot['records']
        finally:
            process.send_signal(signal.SIGINT)
            process.wait(timeout=10)
        assert process.returncode == 0
    recordings = list(capture.glob('*.afolog'))
    assert len(recordings) == 1
    archived = recordings[0].read_bytes()[4096:]
    assert archived == body
    sd_body = (kit / 'breadboard/recording-example.afolog').read_bytes()[4096:]
    sd = {}
    received = {}
    for data, mapping in [(sd_body, sd), (body, received)]:
        for pos in range(0, len(data), 64):
            chunk = data[pos:pos + 64]
            record = decode_record(chunk)
            key = (record.kind, record.sequence)
            assert key not in mapping
            mapping[key] = chunk
    missing = sorted(set(sd) - set(received))
    assert missing == [(7, 5330)]
    assert all(sd[key] == raw for key, raw in received.items())
    run(python, kit, [kit / 'host/convert.py', recordings[0], '--out', out / 'wireless-csv',
                      '--no-plots'], out / 'wireless-conversion-console.txt', expected_exit=2)
    quality = json.loads((out / 'wireless-csv/quality.json').read_text())
    assert quality['sequence_gaps']['emg'] == 1
    assert quality['no_detected_sample_loss'] is False
    assert quality['counts']['emg'] == 10040
    return {'status': 'PASS', 'input_udp_sha256': digest(source),
            'packets': len(packets), 'archived_records': len(body) // 64,
            'archived_records_byte_exact': True, 'missing_from_wireless': missing,
            'wireless_conversion_exit': 2, 'wireless_loss_reported': True,
            'original_saved_file_loss_reported': False,
            'crc_corruption_rejected': after['stats']['invalid_packets'] == 1,
            'duplicate_rejected': after['stats']['reordered_or_duplicate'] == 1,
            'loopback_only': True, 'radio_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, default=Path(sys.executable),
                        help='Python interpreter for the CSV, receiver and regression checks')
    parser.add_argument('--plot-python', type=Path,
                        help='Optional second interpreter with host/requirements.txt installed')
    parser.add_argument('--out', type=Path, required=True, help='New folder for receipts and logs')
    args = parser.parse_args()
    args.out = args.out.absolute()
    args.out.mkdir(parents=True, exist_ok=False)
    # absolute() deliberately preserves the venv interpreter symlink.
    python = args.python.absolute()
    archive = VARIANT / 'breadboard/breadboard-lab-kit.zip'
    report = {'scope': 'Extracted AD7606 fixed-two ICM breadboard kit', 'hardware_measured': False,
              'physical_measurements_completed': 0, 'archive_sha256': digest(archive.read_bytes())}
    try:
        with tempfile.TemporaryDirectory(prefix='afo-kit-standalone-') as folder:
            with zipfile.ZipFile(archive) as zipped:
                assert zipped.testzip() is None
                for name in zipped.namelist():
                    assert (Path(folder) / name).resolve().is_relative_to(Path(folder).resolve())
                zipped.extractall(folder)
            kit = Path(folder) / 'ad7606-two-channel-icm42688-breadboard'
            environment = run(python, kit, ['-c', 'import importlib.util,sys,json; '
                              'print(json.dumps({"python":sys.version.split()[0],'
                              '"matplotlib_installed":importlib.util.find_spec("matplotlib") is not None}))'],
                              args.out / 'python-environment.txt')
            report['csv_test_environment'] = json.loads(environment.stdout)
            run(python, kit, [kit / 'host/check_package.py', '--out', args.out / 'package-check.json'],
                args.out / 'package-check-console.txt')
            report['integrity_and_example'] = json.loads((args.out / 'package-check.json').read_text())
            tests = run(python, kit, [kit / 'host/run_tests.py'], args.out / 'host-tests-console.txt')
            count = re.search(r'Ran (\d+) tests', tests.stderr)
            assert count and int(count[1]) == 46
            report['host_regression_tests'] = {'status': 'PASS', 'tests': 46, 'failures': 0}
            run(python, kit, [kit / 'host/convert.py', kit / 'breadboard/recording-example.afolog',
                              '--out', args.out / 'saved-csv', '--no-plots'],
                args.out / 'saved-conversion-console.txt')
            report['saved_quality'] = json.loads((args.out / 'saved-csv/quality.json').read_text())
            report['receiver_replay'] = replay(python, kit, args.out)
            if args.plot_python:
                run(args.plot_python.absolute(), kit,
                    [kit / 'host/convert.py', kit / 'breadboard/recording-example.afolog',
                     '--out', args.out / 'plots'], args.out / 'plot-conversion-console.txt')
                report['plots'] = {name: {'bytes': (args.out / 'plots' / name).stat().st_size,
                                         'sha256': digest((args.out / 'plots' / name).read_bytes())}
                                   for name in ['signals.png', 'signals.svg']}
                assert all(item['bytes'] > 10000 for item in report['plots'].values())
            else:
                report['plots'] = {'executed': False}
            sample = kit / 'breadboard/recording-example.afolog'
            original = sample.read_bytes()
            corrupted = bytearray(original)
            corrupted[5000] ^= 1
            sample.write_bytes(corrupted)
            result = run(python, kit, [kit / 'host/check_package.py'],
                         args.out / 'tampered-package-console.txt', expected_exit=1)
            assert 'changed package file' in result.stderr
            sample.write_bytes(original)
            report['tampered_recording_rejected'] = True
            report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        (args.out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
