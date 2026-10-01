"""Add an explicit system context around the frozen integrated test fixture.

Peripheral C callbacks and the tested MCU image remain unchanged. Added passive
pins and context blocks draw the physical interfaces; they do not emulate power,
MyoWare electronics, SDMMC or an over-the-air laptop link.
"""
from pathlib import Path
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'web'


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


def build():
    diagram = json.loads((SOURCE / 'diagram.json').read_text())
    diagram['author'] = 'Muttakin Rahman'
    parts = {p['id']: p for p in diagram['parts']}
    positions = {'esp': (400, 60), 'adc': (50, 80), 'foot': (735, 80),
                 'shank': (735, 250), 'logic': (735, 440), 'fixture': (0, 640)}
    for identity, (left, top) in positions.items():
        parts[identity].update(left=left, top=top)
    parts['fixture']['hide'] = True
    # Nominal, known 1 V/2 V inputs: the same case used in the 18-case ledger.
    parts['adc']['attrs'] = {'fault': '0', 'waveform': '0'}
    original_edges = [edge[:2] for edge in diagram['connections']]
    for edge in diagram['connections']:
        if 'fixture:' in ' '.join(edge[:2]) or 'logic:' in ' '.join(edge[:2]):
            edge[2] = ''  # Still connected; measurement/selector wiring is hidden.
        elif 'INT1' in ' '.join(edge[:2]) or 'BUSY' in ' '.join(edge[:2]):
            edge[2] = 'orange'
        else:
            edge[2] = 'green'

    model_specs = {
        'ad7606': ['AIN1', 'AIN2', 'AVCC_5V', 'VIO_3V3', 'GND'],
        'icm42688': ['VDD_3V3', 'GND'],
        'fixture': [],
    }
    for name, extra_pins in model_specs.items():
        # Exact source code, including the already-inlined ADC stimulus table.
        (HERE / f'{name}.chip.c').write_bytes((SOURCE / f'{name}.chip.c').read_bytes())
        definition = json.loads((SOURCE / f'{name}.chip.json').read_text())
        definition['pins'] += extra_pins
        write(f'{name}.chip.json', definition)

    passive = '#include "wokwi-api.h"\n\n// Drawing context only: no pin drive, callbacks or timers.\nvoid chip_init(void) {}\n'
    context = {
        'battery': ('Protected 1S battery / illustrated', ['PACK_PLUS', 'GND']),
        'power': ('Regulated rails / illustrated', ['PACK_PLUS', 'GND', '3V3D', '3V0A', '5V', 'VMID']),
        'myoware': ('MyoWare RAW / synthetic input', ['VIN_3V0', 'GND', 'RAW']),
        'frontend': ('Two RC stages + buffers / ngspice', ['RAW', '3V0A', 'GND', 'VMID', 'TO_ADC']),
        'storage': ('microSD / RAM disk substitute', ['3V3', 'GND', 'CLK', 'CMD', 'D0']),
        'laptop': ('Laptop / internal UDP substitute', ['AFW1_PREVIEW']),
        'radio': ('ESP32 Wi-Fi / logical link', ['AFW1_PREVIEW']),
        'usb': ('USB inlet / illustrated', ['VBUS', 'D_MINUS', 'D_PLUS', 'GND']),
        'monitor': ('Battery + USB sensing / injected', ['BAT', 'VBUS', 'GND', 'BAT_ADC', 'USB_N']),
    }
    for name, (label, pins) in context.items():
        (HERE / f'{name}.chip.c').write_text(passive)
        write(f'{name}.chip.json', {'name': label, 'author': 'Muttakin Rahman', 'pins': pins, 'controls': []})

    def part(kind, identity, left, top, **attrs):
        diagram['parts'].append({'type': kind, 'id': identity, 'left': left, 'top': top, 'attrs': attrs})

    def label(identity, text, left, top):
        part('wokwi-text', identity, left, top, text=text)

    def wire(a, b, color, route=None):
        diagram['connections'].append([a, b, color, route or []])

    part('chip-battery', 'battery', 45, -260)
    part('chip-power', 'power', 360, -260)
    part('chip-myoware', 'myo1', -290, 80)
    part('chip-myoware', 'myo2', -290, 260)
    part('chip-frontend', 'filter1', -120, 80)
    part('chip-frontend', 'filter2', -120, 260)
    part('chip-storage', 'sd', 380, 435)
    part('chip-radio', 'radio', 760, -230)
    part('chip-laptop', 'laptop', 985, -230)
    part('chip-usb', 'usb', 45, -135)
    part('chip-monitor', 'monitor', 190, -135)
    part('wokwi-pushbutton', 'button', 250, 460, color='blue')
    for identity, gpio, color, left in [('rec', 41, 'green', 335), ('err', 42, 'red', 400), ('low', 2, 'yellow', 465)]:
        part('wokwi-led', identity, left, 355, color=color)
        part('wokwi-resistor', identity + '_r', left, 400, value='1000')
        wire(f'esp:{gpio}', f'{identity}_r:1', 'green')
        wire(f'{identity}_r:2', f'{identity}:A', 'green')
        wire(f'{identity}:C', 'esp:GND.1', 'black')
    wire('button:1.l', 'esp:18', 'green')
    wire('button:2.l', 'esp:GND.1', 'black')
    wire('battery:PACK_PLUS', 'power:PACK_PLUS', 'red')
    wire('battery:GND', 'power:GND', 'black')
    wire('power:5V', 'esp:5V', 'red')
    wire('power:5V', 'adc:AVCC_5V', 'red')
    wire('power:3V3D', 'adc:VIO_3V3', 'red')
    wire('power:GND', 'esp:GND.1', 'black')
    wire('adc:GND', 'esp:GND.1', 'black')
    wire('battery:PACK_PLUS', 'monitor:BAT', 'red')
    wire('usb:VBUS', 'monitor:VBUS', 'gray')
    wire('usb:GND', 'esp:GND.1', 'black')
    wire('monitor:GND', 'esp:GND.1', 'black')
    wire('monitor:BAT_ADC', 'esp:1', 'gray')
    wire('monitor:USB_N', 'esp:21', 'gray')
    wire('usb:D_MINUS', 'esp:19', 'gray')
    wire('usb:D_PLUS', 'esp:20', 'gray')
    for identity in ['foot', 'shank']:
        wire('power:3V3D', f'{identity}:VDD_3V3', 'red')
        wire(f'{identity}:GND', 'esp:GND.1', 'black')
    for index in [1, 2]:
        wire('power:3V0A', f'myo{index}:VIN_3V0', 'red')
        wire(f'myo{index}:GND', 'esp:GND.1', 'black')
        wire(f'myo{index}:RAW', f'filter{index}:RAW', 'purple')
        wire('power:3V0A', f'filter{index}:3V0A', 'red')
        wire('power:VMID', f'filter{index}:VMID', 'purple')
        wire(f'filter{index}:GND', 'esp:GND.1', 'black')
        wire(f'filter{index}:TO_ADC', f'adc:AIN{index}', 'purple')
    wire('power:3V3D', 'sd:3V3', 'red')
    wire('sd:GND', 'esp:GND.1', 'black')
    for gpio, pin in [(39, 'CLK'), (47, 'CMD'), (40, 'D0')]:
        # These illustrate the laboratory SDMMC pin assignment. Fixture replaces
        # the driver: the drawn card is passive and the bus is not exercised.
        wire(f'esp:{gpio}', f'sd:{pin}', 'gray')
    wire('radio:AFW1_PREVIEW', 'laptop:AFW1_PREVIEW', 'blue')
    label('title', 'AD7606 / TWO EMG / TWO ICM-42688-P — COMPLETE SYSTEM CONTEXT', -290, -370)
    label('legend', 'Green/orange: executed digital interfaces   Purple: analog chain illustration\nRed/black: ideal power context   Gray: SDMMC replaced by RAM disk   Blue: logical UDP link', -290, -325)
    label('power_note', '3.3 V digital · 3.0 V analog · 5 V ADC · 1.5 V midpoint\nBattery and USB states are injected by the fixture.\nPower, charging, USB transport and runtime are NOT simulated.', 360, -165)
    label('myo_note', 'EMG1 / EMG2\nNo electrodes or person.\n1 V / 2 V known inputs are\ngenerated inside ADC model.\nAnalog response: separate ngspice.', -320, 440)
    label('adc_note', 'AD7606 · ±5 V · OS=0\nCVA/CVB together · all 8 words read\nOnly EMG1/2 exported. Mode straps\nand unused inputs: see lab guide.', 15, 350)
    label('foot_note', 'FOOT / ICM-42688-P / 200 Hz', 735, 40)
    label('shank_note', 'SHANK / ICM-42688-P / 200 Hz', 735, 215)
    label('controls_note', 'REC     ERROR     LOW\nStart/stop shown; automated\nfixture controls this short run.', 320, 300)
    label('storage_note', 'Real FatFS write / sync / reopen\nPSRAM medium substitutes SD card.\nSDMMC wires are context only.', 360, 535)
    label('wifi_note', 'No physical radio/laptop simulation.\nProduction UDP + internal subscriber;\nreal laptop replay tested separately.', 760, -160)
    label('esp_note', 'ESP32-S3 N8R8\nProduction ESP-IDF image + fixture\nUpload merged.bin with F1.\nOutputs: serial file + UDP exports.', 380, -20)
    label('analyzer_note', 'Logic analyzer taps are hidden\nfor clarity; all eight remain connected.', 735, 555)
    write('diagram.json', diagram)
    manifest = {
        'scene': 'complete-system-context', 'default_case': 'normal',
        'production_firmware_changed': False, 'historical_18_case_scene_changed': False,
        'original_executable_edges': original_edges,
        'passive_context_types': list(context),
        'extra_passive_pins': model_specs,
        'scope': 'Original protocol callbacks plus passive system illustrations; not an electrical solver',
        'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                   for f in sorted(HERE.iterdir()) if f.name.endswith(('.chip.c', '.chip.json')) or f.name == 'diagram.json'},
        'frozen_model_c_sha256': {f'{name}.chip.c': hashlib.sha256((SOURCE / f'{name}.chip.c').read_bytes()).hexdigest() for name in model_specs},
    }
    write('manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    result = build()
    print(json.dumps({'parts': len(json.loads((HERE/'diagram.json').read_text())['parts']), 'model_code_unchanged': True, 'scope': result['scope']}))
