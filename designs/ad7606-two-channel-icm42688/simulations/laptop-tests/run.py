#!/usr/bin/env python3
"""Replay captured ESP-IDF UDP through the real laptop receiver and optional browser.

The only edited packet field is synthetic=true in metadata, with a new AFW CRC.
Measurement bytes, sequence gaps and the absence/presence of END are unchanged.
No hardware, RF link, sensor or SDMMC transport is exercised by this test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE.parent.parent
HOST = TARGET / 'host'
sys.path.insert(0, str(HOST))
from afo_format import read_header  # noqa: E402
from live_protocol import decode_packet, encode_packet  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packets(path):
    raw = path.read_bytes()
    at = 0
    out = []
    while at < len(raw):
        if at + 2 > len(raw):
            raise ValueError('truncated UDP length')
        size, = struct.unpack_from('<H', raw, at)
        at += 2
        if at + size > len(raw):
            raise ValueError('truncated UDP payload')
        packet = raw[at:at + size]
        at += size
        decoded = decode_packet(packet)
        if decoded['kind'] == 1:
            meta = dict(decoded['metadata'], synthetic=True)
            packet = encode_packet(1, decoded['boot'], decoded['session'],
                                   decoded['sequence'], json.dumps(meta, separators=(',', ':')).encode(),
                                   dropped=decoded['dropped'])
        out.append(packet)
    if not out:
        raise ValueError('no captured UDP packets')
    return out


def fetch(url):
    with urllib.request.urlopen(url, timeout=2) as response:
        assert response.headers.get('Cache-Control') == 'no-store'
        return response.read(), dict(response.headers)


def wait_for(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(.025)
    raise AssertionError('receiver did not reach the expected state')


def no_payloads(value):
    """The public API supplies decoded measurements, never raw protocol payloads."""
    if isinstance(value, dict):
        assert not ({'payload', 'raw_payload', 'password', 'token', 'wifi_password'} & set(value))
        for child in value.values():
            no_payloads(child)
    elif isinstance(value, list):
        for child in value:
            no_payloads(child)


def browser_check(cli, url, out, case, heartbeat):
    session = 'afo-laptop-' + case
    logs = []

    def call(*args, refresh=True):
        if refresh:
            heartbeat()
        result = subprocess.run([str(cli), '-s=' + session, *args], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        logs.append({'command': list(args), 'returncode': result.returncode, 'output': result.stdout})
        assert result.returncode == 0, 'browser CLI failed: ' + result.stdout[-1500:]
        return result.stdout

    try:
        call('open', url)
        call('snapshot')  # Obtain the current UI before inspecting its rendered contents.
        dom = call('--raw', 'eval', "JSON.stringify({title:document.title,state:document.getElementById('state').textContent,synthetic:getComputedStyle(document.getElementById('demo')).display!=='none',records:document.getElementById('records').textContent,gaps:document.getElementById('gaps').textContent,notice:document.getElementById('notice').textContent,labels:[...document.querySelectorAll('figcaption')].map(x=>x.textContent),foot:document.getElementById('foot').textContent,shank:document.getElementById('shank').textContent,canvas:[...document.querySelectorAll('canvas')].map(c=>{const p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let colored=0;for(let n=0;n<p.length;n+=4)if((p[n+1]>p[n]*1.15&&p[n+1]>p[n+2]*1.1)||(p[n]>p[n+1]*1.1&&p[n+1]>p[n+2]*1.2))colored++;return colored})})")
        # --raw eval prints the JSON string as a JSON-encoded JS result.
        stripped = dom.strip()
        parsed = json.loads(stripped)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        assert parsed['synthetic'] is True
        assert parsed['labels'] == ['EMG1 · ADC input voltage', 'EMG2 · ADC input voltage']
        assert len(parsed['canvas']) == 2 and all(n > 100 for n in parsed['canvas'])
        assert 'Acceleration [g]' in parsed['foot'] and 'Acceleration [g]' in parsed['shank']
        if case == 'normal':
            assert parsed['state'] == 'Recording ended'
            assert parsed['gaps'] == '0'
        else:
            assert parsed['state'] != 'Recording ended'
            assert int(parsed['gaps']) == 158
            assert 'Loss or irregular delivery detected' in parsed['notice']
        screenshot = out / 'output' / 'playwright' / (case + '.png')
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        call('screenshot', '--filename', str(screenshot), '--full-page')
        console = call('console', 'error')
        assert 'Error:' not in console and 'TypeError' not in console
        time.sleep(3.3)
        stale = call('--raw', 'eval', "document.getElementById('state').textContent", refresh=False)
        assert json.loads(stale.strip()) == 'Waiting / link unavailable'
        (out / (case + '-browser.json')).write_text(json.dumps(parsed, indent=2) + '\n')
        return {'pass': True, 'snapshot': parsed,
                'screenshot': str(screenshot.relative_to(out)), 'console_error_free': True,
                'stale_link_state': 'Waiting / link unavailable'}
    finally:
        subprocess.run([str(cli), '-s=' + session, 'close'], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=30)
        (out / (case + '-browser-cli.json')).write_text(json.dumps(logs, indent=2) + '\n')


def run_case(case, out, cli):
    source_dir = TARGET / 'simulations' / 'integrated-recorder' / 'results' / 'current' / case
    source = source_dir / 'udp-output.raw'
    stream = packets(source)
    expected = json.loads((source_dir / 'live-results.json').read_text())
    expected_records = expected['records']
    measurement_body = b''.join(decode_packet(p)['payload'] for p in stream
                                if decode_packet(p)['kind'] == 2)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as device:
        device.bind(('127.0.0.1', 0))
        device.settimeout(5)
        udp_port = device.getsockname()[1]
        # The receiver chooses a kernel-assigned HTTP port; read its announced URL.
        with tempfile.TemporaryDirectory(prefix='afo-laptop-synthetic-') as temp:
            capture = Path(temp) / 'capture'
            log = out / (case + '-receiver.txt')
            with log.open('w') as handle:
                process = subprocess.Popen([sys.executable, str(HOST / 'live_receiver.py'),
                                            '--device', '127.0.0.1', '--udp-port', str(udp_port),
                                            '--http-port', '0', '--out', str(capture), '--no-browser'],
                                           stdout=handle, stderr=subprocess.STDOUT)
                try:
                    hello, peer = device.recvfrom(2048)
                    assert hello == b'AFO-LIVE1'
                    url = wait_for(lambda: next((line.split(': ', 1)[1]
                                                for line in log.read_text().splitlines()
                                                if line.startswith('Live viewer: ')), None))
                    html, _ = fetch(url)
                    assert html == (HOST / 'live_view.html').read_bytes()
                    assert b'<script src=' not in html and b'https://cdn' not in html
                    for packet in stream:
                        device.sendto(packet, peer)
                        time.sleep(.001)  # Bounded replay avoids creating extra host-kernel drops.
                    snapshot = wait_for(lambda: (lambda d: d if d.get('records') == expected_records else None)
                                        (json.loads(fetch(url + 'api')[0])))
                    no_payloads(snapshot)
                    assert snapshot['metadata']['synthetic'] is True
                    assert snapshot['metadata']['active_channel_count'] == 2
                    assert snapshot['metadata']['emg_channels'] == ['EMG1', 'EMG2']
                    assert snapshot['metadata']['adc_model'] == 'AD7606'
                    assert snapshot['metadata']['imu_locations'] == ['foot', 'shank']
                    assert snapshot['stats'] == expected['stats']
                    assert snapshot['imu'] == expected['imu']
                    assert snapshot['health'] == expected['health']
                    assert snapshot['sequence_gaps'] == expected['sequence_gaps']
                    assert snapshot['ended'] == expected['ended']
                    assert snapshot['stop_reason'] == expected['stop_reason']
                    assert len(snapshot['emg']) == 800 and all(len(row) == 5 for row in snapshot['emg'])
                    expected_volts = (6554 * 5 / 32768, 13107 * 5 / 32768)
                    assert all(abs(row[ch + 1] - expected_volts[ch]) < 1e-12
                               for row in snapshot['emg'] for ch in range(2))
                    if case == 'normal':
                        assert snapshot['ended'] is True and snapshot['stop_reason'] == 0
                    else:
                        assert snapshot['ended'] is False and snapshot['stop_reason'] is None
                        assert snapshot['stats']['packet_gaps'] == 158
                    # Metadata heartbeat updates connection age but does not invent new samples.
                    last = decode_packet(stream[-1])
                    last_seq = last['sequence']
                    meta = snapshot['metadata'].copy()
                    meta.pop('transport', None)
                    meta.pop('live_capture', None)
                    def heartbeat():
                        nonlocal last_seq
                        last_seq += 1
                        payload = json.dumps(meta, separators=(',', ':')).encode()
                        device.sendto(encode_packet(1, last['boot'], last['session'], last_seq,
                                                    payload, dropped=last['dropped']), peer)
                    browser = browser_check(cli, url, out, case, heartbeat) if cli else {'executed': False}
                    # CRC failure and duplicate reject after the baseline browser/API check.
                    duplicate = encode_packet(1, last['boot'], last['session'], last_seq,
                                              json.dumps(meta, separators=(',', ':')).encode(),
                                              dropped=last['dropped'])
                    corrupted = bytearray(duplicate)
                    corrupted[-1] ^= 1
                    device.sendto(corrupted, peer)
                    device.sendto(duplicate, peer)
                    after = wait_for(lambda: (lambda d: d if d['stats']['invalid_packets'] == 1
                                            and d['stats']['reordered_or_duplicate'] == 1 else None)
                                     (json.loads(fetch(url + 'api')[0])))
                    assert after['records'] == expected_records
                    assert after['ended'] == expected['ended'] and after['stop_reason'] == expected['stop_reason']
                    no_payloads(after)
                    # Store a compact decoded result, not raw UDP or 800-point API dumps.
                    evidence = {'case': case, 'pass': True, 'hardware_measured': False,
                                'source_udp_sha256': digest(source), 'source_packet_count': len(stream),
                                'record_count': snapshot['records'], 'stats': snapshot['stats'],
                                'sequence_gaps': snapshot['sequence_gaps'], 'ended': snapshot['ended'],
                                'stop_reason': snapshot['stop_reason'], 'enabled_channels': ['EMG1', 'EMG2'],
                                'channel_volts': list(expected_volts), 'imu': snapshot['imu'],
                                'health': snapshot['health'], 'browser': browser,
                                'fault_rejection': {'invalid_packets': after['stats']['invalid_packets'],
                                                   'duplicates': after['stats']['reordered_or_duplicate'],
                                                   'measurements_unchanged': True}}
                finally:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=10)
                assert process.returncode == 0, 'receiver failed to shut down cleanly'
            files = list(capture.glob('*.afolog'))
            assert len(files) == 1
            with files[0].open('rb') as f:
                meta = read_header(f)
                captured_body = f.read()
            assert meta['synthetic'] is True
            assert captured_body == measurement_body, 'receiver altered or omitted original measurement records'
            quality = json.loads((capture / 'wireless_quality.json').read_text())
            session = quality['sessions'][snapshot['session']]
            assert session['records'] == expected_records and session['ended'] == expected['ended']
            assert quality['not_a_replacement_for_sd'] is True
            evidence['archived_measurements_byte_exact'] = True
            evidence['archived_measurements_sha256'] = hashlib.sha256(captured_body).hexdigest()
            evidence['laptop_finalization'] = quality
            converted = Path(temp) / 'converted'
            conversion = subprocess.run([sys.executable, str(HOST / 'convert.py'), str(files[0]),
                                         '--out', str(converted), '--recover', '--no-plots'],
                                        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        timeout=30)
            report = json.loads((converted / 'quality.json').read_text())
            if case == 'normal':
                assert conversion.returncode == 0 and report['no_detected_sample_loss']
                assert report['session_finalized'] and report['signal_checks_pass']
            else:
                assert conversion.returncode == 2 and not report['no_detected_sample_loss']
                assert not report['session_finalized']
                assert any(issue['kind'] == 'missing_end' for issue in report['issues'])
                assert report['sequence_gaps']['emg'] == 1449
                assert report['sequence_gaps']['foot'] == 38 and report['sequence_gaps']['shank'] == 38
            assert report['synthetic'] is True and report['research_ready'] is False
            (out / (case + '-converted-quality.json')).write_text(json.dumps(report, indent=2) + '\n')
            evidence['converter'] = {'returncode': conversion.returncode,
                                     'counts': report['counts'],
                                     'session_finalized': report['session_finalized'],
                                     'no_detected_sample_loss': report['no_detected_sample_loss'],
                                     'signal_checks_pass': report['signal_checks_pass'],
                                     'research_ready': report['research_ready'],
                                     'sequence_gaps': report['sequence_gaps']}
            (out / (case + '.json')).write_text(json.dumps(evidence, indent=2) + '\n')
            return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=HERE / 'results')
    parser.add_argument('--browser-cli', type=Path,
                        help='Optional Playwright CLI or the installed skill wrapper')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = [run_case(case, args.out, args.browser_cli)
               for case in ('normal', 'wireless-packet-loss')]
    summary = {'pass': all(r['pass'] for r in results), 'hardware_measured': False,
               'scope': 'Actual receiver subprocess; loopback UDP; HTTP API; original AFR records; optional live-page browser',
               'synthetic_labeling': 'Only metadata is tagged synthetic=true; record bytes and original sequence gaps are preserved',
               'not_tested': ['Physical radio', 'Real sensors', 'SDMMC/card hardware', 'ESP32-to-laptop physical link'],
               'source_sha256': {str(path.relative_to(TARGET)): digest(path)
                                 for path in (HOST / 'live_receiver.py', HOST / 'live_protocol.py',
                                              HOST / 'live_view.html', HOST / 'afo_format.py',
                                              HOST / 'convert.py', Path(__file__))},
               'cases': results}
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({key: summary[key] for key in ('pass', 'hardware_measured', 'scope')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
