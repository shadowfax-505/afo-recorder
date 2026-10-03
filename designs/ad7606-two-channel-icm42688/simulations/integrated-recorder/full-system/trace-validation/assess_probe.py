"""Qualify an actual Wokwi pin-observer capture against the saved recorder stream.

The project-authored observer samples simulator pins; it does not validate hardware.
Only the first two ADC frames have complete edge logs. Every frame is counted and
decoded by the observer, with first/last frame snapshots and aggregate timing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
sys.path.insert(0, str(P.parent.parent))
from verify_scene import verify as verify_base_scene
import run as integrated

SIGNALS = ['CONVST', 'BUSY', 'CS', 'SCLK', 'DOUTA', 'FOOT_IRQ', 'SHANK_IRQ', 'FOOT_CS', 'RESET']
WORDS = [6554, 13107, -1234, 2345, -32768, 32767, 0, 1111]
ZERO = ['pending', 'bad_clocks', 'bad_words', 'read_while_busy', 'missing_busy',
        'overlapping_conversions', 'prime_outside_reset', 'watch_failures']


def normalize_console(text):
    # The visible Chips Console repeats its chip-name badge for each message.
    # Wokwi splits a long printf into multiple message rows. Remove only those
    # exact standalone badges; leave all message bytes/JSON fields intact.
    text = re.sub(r'(?:^|\r?\n)chip-probe\r?\n[^\S\r\n]*', '', text)
    # Rejoin split stdout chunks, then delimit the instrument's explicit records.
    # No braces, numbers, bit values or missing messages are supplied here.
    return re.sub(r'(?<![\r\n])(?=PROBE_(?:INIT|INITIAL|EDGE|FRAME|SUMMARY|LATE_TRIGGER),)', '\n', text)


def entries(text, marker):
    text = normalize_console(text)
    decoder = json.JSONDecoder()
    return [decoder.raw_decode(text[m.end():].lstrip())[0]
            for m in re.finditer(rf'{marker},', text)]


def independent_edge_decode(text):
    text = normalize_console(text)
    initial = entries(text, 'PROBE_INITIAL')
    if len(initial) != 1 or len(initial[0]['levels']) != len(SIGNALS):
        raise ValueError('Missing or duplicate initial pin snapshot')
    state = dict(zip(SIGNALS, initial[0]['levels']))
    if any(value not in (0, 1) for value in state.values()):
        raise ValueError('Invalid initial logic level')
    rows = re.findall(r'PROBE_EDGE,(\d+),([A-Z0-9_]+),([01])(?:\r?$|\n)', text, re.M)
    frame = None
    decoded = []
    previous = initial[0]['time_ns']
    for t, name, v in rows:
        now, value = int(t), int(v)
        if name not in state or now < previous:
            raise ValueError('Unknown signal or regressing raw edge time')
        previous = now
        old = state[name]
        state[name] = value
        if name == 'CS':
            if not value:
                if frame is not None:
                    raise ValueError('Overlapping raw SPI frames')
                frame = {'start_ns': now, 'bits': [], 'rises': 0}
            elif frame is not None:
                bits = frame.pop('bits')
                if len(bits) != 128 or frame['rises'] != 128:
                    raise ValueError('Incomplete raw 128-clock frame')
                words = []
                for offset in range(0, 128, 16):
                    unsigned = int(''.join(str(x) for x in bits[offset:offset + 16]), 2)
                    words.append(unsigned if unsigned < 32768 else unsigned - 65536)
                if words != WORDS:
                    raise ValueError('Raw DOUTA edge stream disagrees with signed channel order')
                frame.update(end_ns=now, words=words, falls=len(bits))
                decoded.append(frame)
                frame = None
        if name == 'SCLK' and frame is not None and old != value:
            if value:
                frame['rises'] += 1
            else:
                frame['bits'].append(state['DOUTA'])
    if frame is not None or len(decoded) != 2:
        raise ValueError('Raw edge capture must contain exactly two complete ADC frames')
    return {'complete_frames': len(decoded), 'events': len(rows), 'frames': decoded,
            'coverage': 'Actual first two ADC frames only; not a full-session VCD'}


def qualify(text, expected_frames):
    """Reject missing, truncated, incorrectly clocked or mismatched nominal captures."""
    summaries, inits = entries(text, 'PROBE_SUMMARY'), entries(text, 'PROBE_INIT')
    errors = []
    if len(summaries) != 1 or len(inits) != 1:
        raise ValueError('Require exactly one initialized observer and final summary')
    s = summaries[0]
    if s['version'] != 1 or inits[0]['pins'] != 9:
        errors.append('Unexpected observer version or pin count')
    if s['hardware_measured'] is not False or s['drives_outputs'] is not False or inits[0]['drives_outputs'] is not False:
        errors.append('Observer boundary labels missing')
    if expected_frames < 4:
        errors.append('Too few frames for first/last snapshots')
    for name in ZERO:
        if type(s[name]) is not int or s[name] != 0:
            errors.append(f'Observer reports {name}={s[name]}')
    if inits[0]['watch_failures'] or s['partial_frame'] is not False:
        errors.append('Incomplete watch installation or partial last SPI transaction')
    if 'PROBE_LATE_TRIGGER,' in text:
        errors.append('Conversions resumed after the observer reported; capture incomplete')
    for name in ['triggers', 'reads']:
        if s[name] != expected_frames:
            errors.append(f'{name}={s[name]} differs from {expected_frames} saved EMG frames')
    if s['priming_reads'] != 2:
        errors.append('Require two discarded RESET-time reads: initial bus setup and session start')
    expected_counts = {'trigger_period_ns': expected_frames - 1, 'convst_width_ns': expected_frames,
                       'busy_width_ns': expected_frames, 'falling_clock_period_ns': expected_frames * 127}
    bounds = {'trigger_period_ns': (120000, 130000), 'convst_width_ns': (25, 10000),
              'busy_width_ns': (4000, 4000), 'falling_clock_period_ns': (124, 126)}
    for name, count in expected_counts.items():
        metric = s[name]
        low, high = bounds[name]
        if metric['count'] != count or not low <= metric['min'] <= metric['max'] <= high:
            errors.append(f'{name}: count/range outside the nominal model acceptance gate')
        if not metric['count'] * metric['min'] <= metric['sum'] <= metric['count'] * metric['max']:
            errors.append(f'{name}: inconsistent aggregate sum')
    p = s['trigger_period_ns']
    rate = 1e9 * p['count'] / p['sum'] if p['sum'] else 0
    if not 7920 <= rate <= 8080:
        errors.append('Virtual mean trigger rate outside 8 kHz +/-1%')
    span = s['last_trigger_ns'] - s['first_trigger_ns']
    if span != p['sum'] or span <= 0 or s['report_ns'] < s['last_trigger_ns'] + 2000000:
        errors.append('Incomplete or inconsistent acquisition window')
    for identity in ['foot', 'shank']:
        total, window = s[f'{identity}_irq_total'], s[f'{identity}_irq_window']
        period, width = s[f'{identity}_irq_period_ns'], s[f'{identity}_irq_width_ns']
        if not 2 <= total <= 2048 or not max(1, math.floor(span / 5000000) - 1) <= window <= math.ceil(span / 5000000) + 1:
            errors.append(f'{identity}: missing interrupts or incomplete active-window coverage')
        if period['count'] != total - 1 or period['min'] != 5000000 or period['max'] != 5000000 or period['sum'] != period['count'] * 5000000:
            errors.append(f'{identity}: modeled interrupt period differs from 200 Hz')
        # A pulse may still be high at the report boundary, so at most one is open.
        if not total - 1 <= width['count'] <= total or width['min'] != 10000 or width['max'] != 10000 or width['sum'] != width['count'] * 10000:
            errors.append(f'{identity}: modeled interrupt pulse width differs from 10 us')
    frames = entries(text, 'PROBE_FRAME')
    if [f['number'] for f in frames] != [1, 2, expected_frames - 1, expected_frames]:
        errors.append('Missing, duplicate or reordered first/last frame snapshots')
    for f in frames:
        if f['words'] != WORDS or f['falls'] != 128 or f['rises'] != 128:
            errors.append('Frame snapshot has wrong clock count or signed eight-word order')
        if not f['trigger_ns'] + 4000 == f['busy_end_ns'] <= f['cs_start_ns'] < f['cs_end_ns']:
            errors.append('Frame snapshot reads before the modeled conversion completes')
    try:
        decoded = independent_edge_decode(text)
        for raw, snapshot in zip(decoded['frames'], frames[:2]):
            if raw['start_ns'] != snapshot['cs_start_ns'] or raw['end_ns'] != snapshot['cs_end_ns'] or raw['words'] != snapshot['words']:
                errors.append('Independent raw-edge decoder disagrees with observer snapshot')
    except (ValueError, KeyError, IndexError) as exc:
        decoded = {'pass': False, 'error': str(exc)}
        errors.append(str(exc))
    return {'pass': not errors, 'errors': errors, 'hardware_measured': False, 'research_ready': False,
            'engine': 'Actual Wokwi pin-watch callbacks, checked by an independent edge decoder',
            'expected_saved_emg_frames': expected_frames, 'virtual_mean_trigger_rate_hz': rate,
            'observer': s, 'sampled_frames': frames, 'raw_edge_check': decoded,
            'coverage': 'All ADC frames counted/decoded by the observer; detailed raw edges for first two only',
            'clock_idle_polarity_qualified': False,
            'clock_idle_note': 'The observer reports SCLK low at CS assertion in this Wokwi run. '
                'The raw capture decodes falling-edge data and all 128 clocks correctly. '
                'The simulator does not establish the physical controller idle polarity or setup/hold margins.',
            'sclk_low_at_cs_assertions': s['wrong_idle_clock'],
            'priming_note': 'adc_bus_init calls adc_configure once; start_recording calls it again. '
                'Both RESET-time reads are discarded, before the first conversion.',
            'full_session_vcd_qualified': False}


def assess(directory):
    directory = Path(directory)
    base = verify_base_scene()
    manifest = json.loads((directory / 'tested-build.json').read_text())
    root = P.parents[3]
    for name, digest in manifest['sha256'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen recorder source/image changed: ' + name)
    scene = json.loads((directory / 'diagram.json').read_text())
    if scene != json.loads((P / 'diagram.json').read_text()) or scene != json.loads((directory / 'observed-diagram-before-run.json').read_text()):
        raise ValueError('Intended and observed probe scene differ')
    probe_manifest = json.loads((directory / 'probe-manifest.json').read_text())
    for name, digest in probe_manifest['sha256'].items():
        if hashlib.sha256((P / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Probe changed since capture: ' + name)
    serial = (directory / 'serial.txt').read_text()
    prefix = manifest['sha256']['simulations/integrated-recorder/firmware/integrated_recorder.elf'][:9]
    if f'ELF file SHA256:  {prefix}' not in serial:
        raise ValueError('Wrong uploaded ESP32 image')
    with tempfile.TemporaryDirectory(prefix='afo-probe-check-') as temp:
        fresh = Path(temp)
        recording = integrated.assess('normal', serial, fresh)
        for path in fresh.iterdir():
            target = directory / path.name
            if target.exists():
                if path.is_file() and path.read_bytes() != target.read_bytes():
                    raise ValueError('Original export evidence changed: ' + path.name)
                continue
            if path.is_dir(): shutil.copytree(path, target)
            else: shutil.copyfile(path, target)
    pin_text = (directory / 'chips-console.txt').read_text()
    pin_check = qualify(pin_text, recording['production']['emg'])
    result = {'pass': recording['pass'] and pin_check['pass'], 'hardware_measured': False,
              'research_ready': False, 'base_scene_checks': base, 'recording': recording,
              'pin_checks': pin_check, 'probe_input_manifest': probe_manifest,
              'sha256': {n: hashlib.sha256((directory / n).read_bytes()).hexdigest()
                         for n in ['serial.txt', 'chips-console.txt', 'diagram.json', 'tested-build.json']}}
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = assess(args.directory)
    print(json.dumps({'pass': result['pass'], 'pin_checks': result['pin_checks']}, indent=2))
    raise SystemExit(0 if result['pass'] else 1)
