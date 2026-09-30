#!/usr/bin/env python3
"""Execute production recording control logic with injected RTOS/filesystem results."""
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
VARIANT = HERE.parents[1]
MAIN = VARIANT / 'firmware/main'
sys.path.insert(0, str(VARIANT / 'host'))
from afo_format import HEADER_SIZE, make_header, read_header
from convert import convert
from live_protocol import decode_packet, encode_packet
from live_receiver import Capture

CASES = (
    'normal', 'short-writes-eintr', 'worker-fault-before-join', 'queue-overflow',
    'body-write-failure', 'partial-write-failure', 'zero-byte-write',
    'header-write-failure', 'header-sync-failure', 'data-sync-failure',
    'end-sync-failure', 'close-failure', 'emg-task-create-failure',
    'imu-task-create-failure', 'imu-stop-failure', 'usb-attached',
    'usb-during-recording', 'battery-low', 'card-full',
)
API_HEADERS = (
    'esp_err.h', 'esp_vfs_fat.h', 'esp_timer.h', 'esp_random.h', 'esp_log.h',
    'driver/gpio.h', 'driver/sdmmc_host.h', 'freertos/FreeRTOS.h',
    'freertos/task.h', 'freertos/queue.h', 'freertos/event_groups.h',
)


def run():
    results = []
    destination = HERE / 'results'
    destination.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='afo-recorder-control-') as temp_name:
        temp = Path(temp_name)
        includes = temp / 'include'
        for name in API_HEADERS:
            path = includes / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#include "shim.h"\n')
        for profile in ('pcb', 'breadboard'):
            binary = temp / f'recorder-{profile}'
            command = [os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                       '-Werror', '-Wno-unused-function', '-Wno-unused-const-variable',
                       '-I', str(HERE), '-I', str(includes), '-I', str(MAIN),
                       f'-DAFO_BREADBOARD={int(profile == "breadboard")}',
                       f'-DHARDWARE_VARIANT="{profile}"', str(HERE / 'test_recorder.c'),
                       '-o', str(binary)]
            subprocess.run(command, check=True)
            for case in CASES:
                folder = temp / f'{profile}-{case}'
                folder.mkdir()
                process = subprocess.run([str(binary), case, str(folder)],
                                         capture_output=True, text=True, timeout=10)
                if process.returncode:
                    raise RuntimeError(f'{profile}/{case}: {process.stderr}')
                control = json.loads((folder / 'control.json').read_text())
                control['profile'] = profile
                raw_metadata = (folder / 'metadata.json').read_bytes()
                if raw_metadata:
                    # Exact production JSON must fit AFW1 and remain decodable.
                    packet = encode_packet(1, 1, 1, 1, raw_metadata)
                    metadata = decode_packet(packet)['metadata']
                    assert metadata['active_channel_count'] == 2
                    assert metadata['hardware_variant'] == profile
                    assert metadata['sd_cmd_gpio'] == (47 if profile == 'breadboard' else 38)
                    assert metadata['input_midpoint_mv'] == 0
                    control['metadata_roundtrip_pass'] = True
                raw_live = (folder / 'live-records.bin').read_bytes()
                records = []
                for pos in range(0, len(raw_live), 16 * 64):
                    payload = raw_live[pos:pos + 16 * 64]
                    decoded = decode_packet(encode_packet(2, 1, 1, pos // 1024 + 2,
                                                         payload, len(payload) // 64))
                    records.extend(decoded['records'])
                if records:
                    assert records[-1].kind == 5 and records[-1].flags == control['reason']
                    control['live_end_reason_pass'] = True
                    capture = Capture(folder / 'laptop-capture')
                    try:
                        capture.accept(encode_packet(1, 1, 1, 1, raw_metadata))
                        for pos in range(0, len(raw_live), 16 * 64):
                            payload = raw_live[pos:pos + 16 * 64]
                            capture.accept(encode_packet(2, 1, 1, pos // 1024 + 2,
                                                         payload, len(payload) // 64))
                        state = capture.snapshot()
                        assert state['ended'] and state['stop_reason'] == control['reason']
                        assert state['metadata']['active_channel_count'] == 2
                        if state['emg']:
                            assert len(state['emg'][-1]) == 5  # time, two voltages, sequence, flags
                        control['laptop_stop_state_pass'] = True
                    finally:
                        capture.close()
                raw_disk = (folder / 'raw-disk.afolog').read_bytes()
                if control['stream_started'] and control['reason'] != 1:
                    assert raw_disk[-64:] == raw_live[-64:]
                    control['sd_live_end_identical'] = True
                if len(raw_disk) >= HEADER_SIZE:
                    metadata = read_header(io.BytesIO(raw_disk))
                    # Never publish a simulated fixture as a real human recording.
                    metadata.update(synthetic=True, simulation_engine='native production recorder API shim')
                    marked = make_header(metadata) + raw_disk[HEADER_SIZE:]
                    fixture_dir = destination / profile / case
                    fixture_dir.mkdir(parents=True, exist_ok=True)
                    source = fixture_dir / 'simulated.afolog'
                    source.write_bytes(marked)
                    export = folder / 'export'
                    quality = convert(source, export, recover=True, make_plots=False)
                    (fixture_dir / 'quality.json').write_text(json.dumps(quality, indent=2) + '\n')
                    control['quality'] = quality
                    if case in ('normal', 'short-writes-eintr'):
                        assert quality['session_finalized'] and quality['no_detected_sample_loss']
                        assert quality['counts']['emg'] == 260
                        assert quality['counts']['foot'] == quality['counts']['shank'] == 6
                    if case == 'partial-write-failure':
                        assert not quality['session_finalized'] and quality['issues']
                    if case not in ('normal', 'short-writes-eintr', 'end-sync-failure', 'close-failure'):
                        assert not quality['no_detected_sample_loss']
                control['sd_commit_checks_pass'] = control['stream_started'] and control['reason'] != 1
                if case in ('end-sync-failure', 'close-failure'):
                    # The bytes may contain END even though the filesystem operation
                    # failed. A converter cannot certify persistence from bytes alone.
                    assert control['quality']['session_finalized']
                    assert not control['sd_commit_checks_pass'] and control['live_end_reason_pass']
                control['pass'] = True
                results.append(control)
                print(f'PASS {profile}/{case}', flush=True)
    report = {
        'engine': 'native C compiler; production main.c and format.c; mocked ESP-IDF APIs',
        'cases_per_profile': len(CASES), 'profiles': ['pcb', 'breadboard'],
        'cases_passed': len(results), 'hardware_measured': False, 'esp32_executed': False,
        'production_sources_sha256': {name: hashlib.sha256((MAIN / name).read_bytes()).hexdigest()
                                      for name in ('main.c', 'format.c', 'board.h', 'variant.h')},
        'limits': [
            'Deterministic control-flow shims; no real FreeRTOS scheduler, concurrent cores or ISR execution',
            'EMG/IMU records are injected through production enqueue; sensor acquisition is tested separately',
            'No physical SDMMC, flash persistence, radio transport, noise, power or runtime measurements',
            'Late sync/close failures can leave an END marker among visible bytes; END alone cannot certify durability',
        ],
        'results': results,
    }
    (destination / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(results)} production recorder control cases passed; no hardware measured.')


if __name__ == '__main__':
    run()
