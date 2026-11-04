#!/usr/bin/env python3
"""Build docs/main-setup-reference.pdf: a current, single-file reference for this setup.

Tables (GPIO map, firmware profiles, build stages, Wokwi results, parts) are read from
the package files so the PDF follows the sources; prose states the firmware 1.12 state.
"""
from pathlib import Path
import json, csv, html, re, math, datetime
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, Image, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

P = Path(__file__).resolve().parents[1]
D = P / 'docs'
OUT = D / 'main-setup-reference.pdf'
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('Sans', FONT_DIR / 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Bold', FONT_DIR / 'DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('Mono', FONT_DIR / 'DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Sans-Bold', italic='Sans', boldItalic='Sans-Bold')

TEAL = colors.HexColor('#096b60'); INK = colors.HexColor('#172c29'); LIGHT = colors.HexColor('#e8f2ee')
AMBER = colors.HexColor('#fff4dc'); AMBER_LINE = colors.HexColor('#c98a12'); GRID = colors.HexColor('#cadbd4')
W = 499


def style(name, size, leading, bold=False, color=INK, **kw):
    kw.setdefault('fontName', 'Sans-Bold' if bold else 'Sans')
    return ParagraphStyle(name, fontSize=size, leading=leading,
                          textColor=color, splitLongWords=True, **kw)


ST = {
    'body': style('body', 9.6, 14, spaceAfter=7),
    'small': style('small', 8, 11),
    'cell': style('cell', 7.6, 10.2),
    'cellb': style('cellb', 7.6, 10.2, bold=True),
    'h1': style('h1', 18, 23, bold=True, color=TEAL, spaceAfter=9, keepWithNext=True),
    'h2': style('h2', 11.5, 15, bold=True, color=TEAL, spaceBefore=6, spaceAfter=5, keepWithNext=True),
    'cover': style('cover', 30, 36, bold=True, color=TEAL, spaceAfter=8),
    'sub': style('sub', 13, 18, color=INK, spaceAfter=4),
    'code': style('code', 8, 11, fontName='Mono', backColor=colors.HexColor('#f3f6f5'), borderPadding=5,
                  spaceBefore=3, spaceAfter=9, leftIndent=5, rightIndent=5),
    'toc0': style('toc0', 9.6, 15),
}


def inline(t):
    t = html.escape(t)
    t = re.sub(r'`([^`]+)`', r'<font name="Mono">\1</font>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    return t


def p(t, st='body'):
    return Paragraph(inline(t), ST[st])


def bullets(items):
    return [Paragraph('•&nbsp;&nbsp;' + inline(i), style('b', 9.6, 14, leftIndent=12, firstLineIndent=-9, spaceAfter=3))
            for i in items] + [Spacer(1, 5)]


def code(t):
    return Paragraph(html.escape(t).replace('\n', '<br/>'), ST['code'])


def table(rows, widths, head=True, mono_cols=()):
    data = []
    for r, row in enumerate(rows):
        cells = []
        for c, v in enumerate(row):
            txt = inline(str(v))
            if c in mono_cols and r > 0:
                txt = '<font name="Mono">' + html.escape(str(v)) + '</font>'
            cells.append(Paragraph(txt, ST['cellb' if head and r == 0 else 'cell']))
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0, hAlign='LEFT')
    cmds = [('GRID', (0, 0), (-1, -1), .4, GRID), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
    if head:
        cmds.append(('BACKGROUND', (0, 0), (-1, 0), LIGHT))
    t.setStyle(TableStyle(cmds))
    return [t, Spacer(1, 10)]


def callout(text):
    t = Table([[Paragraph(inline(text), ST['body'])]], colWidths=[W])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), AMBER), ('LINEBEFORE', (0, 0), (0, -1), 3, AMBER_LINE),
                           ('LEFTPADDING', (0, 0), (-1, -1), 10), ('TOPPADDING', (0, 0), (-1, -1), 7),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return [t, Spacer(1, 10)]


def figure_image(path, width):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(path)).getSize()
    return Image(str(path), width=width, height=width * ih / iw)


# ---------- drawings ----------
def box(d, x, y, w, h, label, fill=LIGHT):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=TEAL))
    lines = label.split('|')
    for i, line in enumerate(lines):
        d.add(String(x + w / 2, y + h / 2 + (len(lines) - 1) * 5.5 - 3 - i * 11, line, textAnchor='middle',
                     fontName='Sans', fontSize=8, fillColor=INK))


def arrow(d, x, y, a, b):
    d.add(Line(x, y, a, b, strokeColor=TEAL, strokeWidth=1.3))
    ang = math.atan2(b - y, a - x); u = 6
    d.add(Polygon([a, b, a - u * math.cos(ang - .5), b - u * math.sin(ang - .5),
                   a - u * math.cos(ang + .5), b - u * math.sin(ang + .5)], fillColor=TEAL, strokeColor=None))


def architecture():
    d = Drawing(W, 215)
    for x, label in [(0, '2 × MyoWare 2.0|RAW outputs'), (128, '2 × buffered|RC low-pass'),
                     (256, 'AD7606|8 kHz CONVST'), (384, 'ESP32-S3|N8R8')]:
        box(d, x, 140, 112, 52, label)
    for x in (112, 240, 368):
        arrow(d, x, 166, x + 16, 166)
    box(d, 200, 40, 140, 52, 'Foot + shank ICM-42688-P|SPI3, 200 Hz, INT1')
    arrow(d, 340, 66, 420, 140)
    box(d, 384, 40, 115, 52, 'microSD (primary)|Wi-Fi preview')
    arrow(d, 440, 140, 440, 92)
    box(d, 0, 40, 160, 52, 'Protected 1S battery|3V3D · 3V0A · 5V_ADC', fill=colors.white)
    d.add(String(0, 12, 'Functional paths only; not physical header positions.', fontName='Sans', fontSize=8, fillColor=TEAL))
    return d


def filter_plot():
    d = Drawing(W, 190); x0, y0, w, h = 45, 35, 430, 140
    for db in (0, -10, -20, -30):
        y = y0 + h * (db + 30) / 30
        d.add(Line(x0, y, x0 + w, y, strokeColor=colors.lightgrey))
        d.add(String(5, y - 3, f'{db} dB', fontName='Sans', fontSize=7.5))
    prev = None
    for i in range(151):
        f = 10 ** (1 + i * math.log10(400) / 150)
        db = -20 * math.log10(1 + (2 * math.pi * f * 3300 * 47e-9) ** 2)
        q = (x0 + w * i / 150, y0 + h * (db + 30) / 30)
        if prev:
            d.add(Line(*prev, *q, strokeColor=TEAL, strokeWidth=2))
        prev = q
    for f in (10, 100, 500, 1000, 4000):
        d.add(String(x0 + w * math.log10(f / 10) / math.log10(400) - 8, 20, str(f), fontName='Sans', fontSize=7.5))
    d.add(String(170, 4, 'Frequency (Hz), log scale · two ideal 3.3 kΩ / 47 nF poles', fontName='Sans', fontSize=7.5))
    return d


# ---------- document ----------
def footer(c, doc):
    c.saveState()
    c.setStrokeColor(GRID); c.line(48, 40, 547, 40)
    c.setFont('Sans', 7.5); c.setFillColor(TEAL)
    c.drawString(48, 27, 'AFO Research Recorder · AD7606 / 2 EMG / ICM-42688-P · firmware ad7606-2ch-1.12')
    c.drawRightString(547, 27, str(doc.page))
    c.restoreState()


class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=(595, 842), leftMargin=48, rightMargin=48, topMargin=48,
                         bottomMargin=58, title='Main setup reference: AD7606 · two EMG · ICM-42688-P',
                         author='Muttakin Rahman', subject='AFO Research Recorder')
        self.addPageTemplates(PageTemplate(id='n', frames=[Frame(48, 58, W, 736, id='f', leftPadding=0,
                              rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer))

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == 'h1':
            text = f.getPlainText(); key = 'h' + str(abs(hash(text)))
            self.canv.bookmarkPage(key); self.canv.addOutlineEntry(text, key, 0)
            self.notify('TOCEntry', (0, text, self.page, key))


def load():
    j = lambda rel: json.loads((P / rel).read_text())
    profiles = []
    for m in sorted((P / 'firmware/builds').glob('*/manifest.json')):
        profiles.append(json.loads(m.read_text()))
    return {
        'gpio': j('design/gpio-map.json'),
        'stages': j('development/stage-plan.json'),
        'web': j('simulations/integrated-recorder/results/web-1.12/summary.json'),
        'audit': j('simulations/integrated-recorder/results/web-1.12/timing-audit.json'),
        'profiles': profiles,
        'parts': (D / 'selected-lab-parts.md').read_text(),
        'bom': list(csv.DictReader((P / 'hardware/main/bom.csv').open())),
    }


PROFILE_USE = {
    'diagnostic-controller': ('2', 'Controller, button, LEDs, USB sense'),
    'diagnostic-adc': ('3–5', 'AD7606 and the analog paths, added one at a time'),
    'diagnostic-imu-one': ('6', 'Adds the foot ICM carrier'),
    'diagnostic-imu-two': ('6', 'Adds the shank ICM carrier'),
    'diagnostic-imu-bench-one': ('any', 'DevKit + one carrier only; 60 s PASS/FAIL verdicts'),
    'diagnostic-imu-bench-two': ('any', 'DevKit + both carriers only; 60 s PASS/FAIL verdicts'),
    'breadboard-sd-only-2ch': ('7', 'Full breadboard, SD recording, Wi-Fi off'),
    'breadboard-record-2ch': ('8–10', 'Full breadboard, SD + best-effort Wi-Fi preview'),
    'record-2ch': ('PCB', 'Compact PCB only (SD CMD on GPIO38)'),
}
PROFILE_ORDER = list(PROFILE_USE)

CASE_TEXT = {
    'normal': 'Nominal recording', 'write-delay-50ms': '50 ms SD write delay', 'queue-stall-350ms': '350 ms queue stall',
    'storage-write-error': 'SD write error', 'usb-attached-during-recording': 'USB attached mid-recording',
    'battery-low': 'Battery low', 'adc-stuck-busy': 'ADC BUSY stuck high', 'imu-fifo-overflow': 'IMU FIFO overflow',
    'imu-missing-interrupt': 'IMU interrupt missing', 'no-wireless-subscriber': 'No laptop listening',
    'wireless-packet-loss': 'Wi-Fi packet loss', 'interrupted-recording': 'Power cut mid-recording',
    'storage-mount-failure': 'SD mount failure', 'full-card-refusal': 'Full card at start',
    'filtered-synthetic-emg': 'Filtered synthetic EMG', 'absent-shank': 'Shank IMU absent',
    'adc-busy-stays-low': 'ADC BUSY never rises', 'adc-trigger-ignored': 'ADC ignores CONVST',
}


STOP_NAMES = {}  # filled from firmware/main/main.c


def case_outcome(c):
    if c.get('refused') or c.get('reason'):
        return (c.get('reason') or 'Start refused').strip().rstrip(':') + ' (expected)'
    pr = c.get('production') or {}
    q = (c.get('quality') or {}).get('counts') or {}
    parts = []
    if q:
        parts.append(f"{q.get('emg', 0):,} EMG / {q.get('foot', 0)} foot / {q.get('shank', 0)} shank saved")
    if pr.get('fault'):
        parts.append(f"stopped with reason {STOP_NAMES.get(pr['fault'], pr['fault'])}, as expected")
    elif q and not (c.get('quality') or {}).get('session_finalized'):
        parts.append('no END; synced records recovered, as expected')
    elif q:
        parts.append('normal stop')
    return '; '.join(parts) or 'Pass'


def build():
    data = load()
    enum = re.search(r'enum[^{]*\{([^}]*STOP_USB[^}]*)\}', (P / 'firmware/main/main.c').read_text(), re.S)[1]
    for name, num in re.findall(r'STOP_([A-Z]+)\s*=\s*(\d+)', enum):
        STOP_NAMES[int(num)] = name.lower()
    story = []
    today = datetime.date(2026, 10, 12).strftime('%-d %B %Y')

    # Cover
    story += [Spacer(1, 40), p('AFO RESEARCH RECORDER', 'h2'), Paragraph('Main setup reference', ST['cover']),
              p('AD7606 · two MyoWare 2.0 EMG channels · two ICM-42688-P motion sensors', 'sub'),
              p(f'Package `ad7606-two-channel-icm42688` · firmware `ad7606-2ch-1.12` · {today}', 'body'),
              p('Project lead: Muttakin Rahman', 'body'), Spacer(1, 14), architecture(), Spacer(1, 14)]
    story += callout('**Engineering prototype.** Firmware, file format, host tools, PCB rules, wiring and simulations have '
                     'automated evidence. No assembled recorder has yet passed the physical bench sequence. Nothing here '
                     'claims measured signal quality, battery runtime, wearable safety or clinical performance.')
    story += [p('This document collects, in one place, what the main setup is, how it is wired and powered, which '
                'firmware image to flash at each build stage, what the simulations have shown and what is still open. '
                'It is generated from the package files, so its tables match the repository at the date above.', 'body'),
              PageBreak()]

    toc = TableOfContents(); toc.levelStyles = [ST['toc0']]
    story += [Paragraph('Contents', ST['h2']), Spacer(1, 6), toc, PageBreak()]

    # 1. At a glance
    story += [Paragraph('1. The setup at a glance', ST['h1'])]
    story += [p('This is the reference configuration of the project: the fixed two-input recorder. Two bare MyoWare 2.0 '
                'sensors feed their RAW outputs through two buffered low-pass stages into an AD7606 simultaneous-sampling '
                'ADC. An ESP32-S3 triggers conversions at 8 kHz, reads two ICM-42688-P carriers (foot and shank) at '
                '200 Hz each, writes every record to microSD and sends a best-effort live copy to a laptop over Wi-Fi.')]
    story += table([
        ['Item', 'Value'],
        ['EMG inputs', '2 fixed (EMG1, EMG2), single-ended MyoWare RAW; four-channel builds are rejected'],
        ['EMG sampling', '8 kHz per channel; both channels converted simultaneously on one CONVST edge'],
        ['ADC', 'AD7606, 16-bit, ±5 V range, oversampling off; 152.588 µV per code; serial mode 2 at 8 MHz'],
        ['Analog path', 'Two 3.3 kΩ / 47 nF poles with unity buffers; about −1.85 dB at 500 Hz, −3 dB near 660 Hz'],
        ['Motion', 'Two ICM-42688-P (MIKROE-4237 carriers), 200 Hz accel + gyro, ±16 g / ±2000 °/s, SPI3'],
        ['Controller', 'ESP32-S3-WROOM-1 N8R8 (PCB) or ESP32-S3-DevKitC-1 N8R8 (breadboard)'],
        ['Primary storage', 'microSD over SDMMC 1-bit; 64-byte CRC-protected records; 2.44 s PSRAM record queue'],
        ['Live preview', 'Private WPA2 access point `AFO-Recorder-B`; per-device password generated on first boot'],
        ['Power', 'Protected 1S Li-ion; 3V3D digital, 3V0A analog, 5V_ADC for AVCC; USB is sense-only'],
        ['Firmware', '`ad7606-2ch-1.12`, ESP-IDF v5.4.2, nine profiles'],
        ['Simulation', 'All 18 integrated Wokwi cases pass on the 1.12 image (12 October 2026)'],
        ['Physical status', 'Not built or measured; compact PCB not ordered'],
    ], [110, W - 110])

    story += [Paragraph('2. Parts', ST['h1']), p('**Laboratory (breadboard) build.** These are the selected modules for the '
              'staged bench build. Use one package end to end; do not mix MPU-6050 or four-channel parts or firmware.', 'body')]
    rows = [['Function', 'Selected part', 'Boundary']]
    for line in data['parts'].splitlines():
        if line.startswith('|') and not line.startswith('|---') and not line.startswith('|Function'):
            rows.append([c.strip() for c in line.strip('|').split('|')])
    story += table(rows, [80, 150, W - 230])
    key = {'U1', 'U2', 'J1', 'J2', 'J3', 'J4', 'Q2', 'D1', 'D30', 'R70'}
    pcb = [['Ref', 'Value', 'Part number']] + [[b['Reference'], b['Value'], b['MPN']] for b in data['bom']
                                                if b['Reference'] in key or b['Reference'].startswith(('U', 'D3'))]
    story += [p('**Compact PCB, key parts** (full list: `hardware/main/bom.csv`, '
                f"{len(data['bom'])} lines). D30 and R70 were added on 12 October 2026 for the AD7606 supply-ramp fix.")]
    story += table(pcb, [60, 190, W - 250])

    # 3. Signal chain
    story += [Paragraph('3. EMG signal chain', ST['h1'])]
    story += [p('Each MyoWare RAW output passes a 3.3 kΩ / 47 nF low-pass section, a unity buffer, a second 3.3 kΩ / '
                '47 nF section and another unity buffer, then 100 Ω in series and 1 nF to ground at the AD7606 input. '
                'V1 and V2 are single-ended; V3–V8 are grounded on this board. All eight conversion words are clocked '
                'out, and only V1 and V2 are exported.'),
              p('A 1 MΩ resistor biases an unplugged RAW port toward the buffered 1.5 V midpoint. This is not an '
                'offset stage: the converter reconstructs the connector voltage with `input_scale=1` and '
                '`input_midpoint_mv=0`, and records the bias separately as `unplugged_input_bias_mv=1500`.'),
              filter_plot(), Spacer(1, 6)]
    story += table([
        ['Frequency', 'Nominal gain', 'Expected rms_ac_codes (100 mVpp sine)'],
        ['20 Hz', '−0.00 dB', '231.6'], ['100 Hz', '−0.08 dB', '229.5'],
        ['500 Hz', '−1.85 dB', '187.2'], ['1000 Hz', '−5.80 dB', '118.8'],
    ], [110, 110, W - 220])
    story += [p('**Scaling.** Volts at the ADC input = code × 5 / 32768 (152.588 µV per code). A 0–3 V sensor uses about '
                '30 % of the bipolar code range, so “16-bit” describes the word, not 16 effective bits at the muscle. '
                'Reference, gain, offset and noise need bench calibration.'),
              p('**Protection.** BAV199 clamps (ground → junction → 3V0A) sit at the first filter node. They do not make '
                'the connector tolerant of arbitrary ±5 V or ±10 V signals; keep test signals within 0–3 V.')]

    # 4. Power
    story += [Paragraph('4. Power and the AD7606 supply ramp', ST['h1'])]
    story += bullets([
        'A protected single-cell pack enters through a reverse-polarity P-channel MOSFET. Charging is external.',
        'TPS63070 buck-boost makes 3V3D (nominal 3.328 V) for the ESP32, IMUs, SD and AD7606 VDRIVE.',
        'TPS7A2030 LDO makes 3V0A for the MyoWare sensors and buffers; the buffered midpoint is 1.5 V.',
        'TPS60150 charge pump makes 5V_ADC (AVCC, 4.75–5.25 V) from 3V3D.',
        'USB VBUS is sense-only (2N7002, active-low GPIO21). Recording is refused while USB is attached.',
    ])
    story += [Paragraph('Supply-ramp fix (PCB, 12 October 2026)', ST['h2']),
              p('Because AVCC is generated from 3V3D, VDRIVE rises before AVCC, which conflicts with the AD7606 '
                'absolute maximum VDRIVE ≤ AVCC + 0.3 V and with ADI AN-1091. The PCB now holds the converter in full '
                'shutdown until both rails are up:')]
    story += bullets([
        'AD7606 STBY (pin 7) runs on net ADC_STBY to GPIO14, with R70 (100 kΩ) pulling it low; RANGE stays low.',
        'D30 (BAT760 Schottky) from 3V3D to 5V_ADC limits VDRIVE − AVCC while the charge pump starts.',
        'Firmware (PCB builds, from 1.11) releases STBY once per boot, waits the 30 ms wake-up time, then resets the ADC.',
        'KiCad DRC 0 violations / 0 unconnected, ERC 0. Breadboard builds are unchanged: the module straps STBY.',
    ])
    story += table([
        ['Bench rail', 'Stage-1 acceptance'],
        ['3V3D digital', '3.23–3.43 V at 0 / 100 / 300 mA; ripple ≤ 50 mVpp (20 MHz bandwidth)'],
        ['3V0A analog', '2.94–3.06 V at 0 / 20 / 50 mA; midpoint 0.49–0.51 × rail; ripple ≤ 10 mVpp'],
        ['5 V ADC', '4.8–5.2 V at 10–50 mA; never above 5.25 V during start-up'],
    ], [110, W - 110])

    # 5. GPIO
    story += [Paragraph('5. ESP32-S3 pin map', ST['h1']),
              p('From `design/gpio-map.json` (compact PCB). The only breadboard difference is SD CMD: **GPIO47 on the '
                'DevKit breadboard, GPIO38 on the PCB**, because the DevKit drives an RGB LED on GPIO38. Flash the '
                'matching build.')]
    gp = sorted(data['gpio'].items(), key=lambda kv: int(kv[0]))
    half = (len(gp) + 1) // 2
    rows = [['GPIO', 'Net', 'GPIO', 'Net']]
    for i in range(half):
        a = gp[i]; b = gp[i + half] if i + half < len(gp) else ('', '')
        rows.append([a[0], a[1], b[0], b[1]])
    story += table(rows, [50, 199, 50, 200], mono_cols=(1, 3))
    story += [p('AD7606 CVA and CVB share GPIO11 (CONVST). The net named ADC_DRDY carries BUSY: the AD7606 has no '
                'separate data-ready output. SPI2 runs at 8 MHz, mode 2 (idle high, falling-edge sample). The IMUs '
                'share SPI3 on GPIO4/5/6 with separate chip selects (foot GPIO7, shank GPIO15) and INT1 lines '
                '(foot GPIO16, shank GPIO17). Full contact-level tables: `docs/build-guide.html`.')]

    # 6. IMU
    story += [Paragraph('6. Motion sensors and timing', ST['h1'])]
    story += bullets([
        'MIKROE-4237 carriers with JP2–JP4 in the SPI position (pads 1–2), 3.3 V supply, mikroBUS orientation as drawn.',
        'Firmware checks WHO_AM_I = 0x47 and configuration readback, then sets 200 Hz, ±16 g, ±2000 °/s, 16-byte FIFO packets.',
        'FIFO timestamp ticks last 32/30 µs on the ICM-42688 (TDK driver PLL scale; datasheet section 12.7). Expect a '
        'tick step of about 4,687.5 per 200 Hz sample.',
        'The datasheet allows ±1.5 % clock error at 25 °C and ±2 % over temperature; the stage-6/7 gates use ±2 %.',
        'Each sensor has its own clock. The converter adds `host_time_fitted_us`, a least-squares fit of every interrupt '
        'anchor, to align IMU samples with EMG. Times remain flagged as estimates until bench timing is characterised.',
    ])

    # 7. Firmware
    story += [Paragraph('7. Firmware 1.12 and its profiles', ST['h1']),
              p('All profiles are built from one source set, `ad7606-2ch-1.12`, with ESP-IDF v5.4.2 for the ESP32-S3. '
                'Flash the bootloader, partition table and application from **one** profile at its manifest offsets '
                '(`0x0`, `0x8000`, `0x10000`). Keep the application hash with every measured run. The binaries are '
                'cross-compiled only; none has been flashed to an assembled recorder.')]
    rows = [['Stage', 'Profile', 'Use', 'application.bin SHA-256 (first 16)']]
    by = {m['profile']: m for m in data['profiles']}
    for name in PROFILE_ORDER + sorted(set(by) - set(PROFILE_ORDER)):
        if name in by:
            st, use = PROFILE_USE.get(name, ('', ''))
            rows.append([st, name, use, by[name]['sha256']['application.bin'][:16]])
    story += table(rows, [40, 140, 189, 130], mono_cols=(1, 3))
    story += [Paragraph('What changed recently', ST['h2'])]
    story += table([
        ['Version', 'Change'],
        ['1.12', 'The Wi-Fi live task announces a new session (metadata packet) before that session\'s first data '
                 'packet. On 1.11 a record dequeued just after the metadata check could go first, and the laptop '
                 'dropped it as an unknown session. Found by the Wokwi IMU missing-interrupt case.'],
        ['1.11', 'PCB builds release AD7606 STBY on GPIO14, wait 30 ms, then reset (ADI AN-1091).'],
        ['1.10', 'Official ICM-42688-P datasheet cross-check; clock gates widened to ±2 %; `within_datasheet_tolerance`.'],
        ['1.9', 'IMU-only bench diagnostics with PASS/FAIL verdicts; register-level ICM model.'],
        ['1.8', 'ICM FIFO ticks converted as 32/30 µs instead of 1 µs.'],
        ['1.7', 'PSRAM record queue of 20,480 records (2.44 s); no compiled Wi-Fi password; 1,400-byte metadata limit.'],
    ], [50, W - 50])
    story += [Paragraph('Rebuilding', ST['h2']),
              code('cd firmware\n'
                   'idf.py -B build-breadboard-2 -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=breadboard \\\n'
                   '       -DAFO_WIFI=1 -DAFO_DIAGNOSTIC_STAGE=0 -DAFO_IMU_COUNT=2 build\n'
                   'idf.py -B build-pcb-2 -DEMG_CHANNEL_COUNT=2 -DAFO_HARDWARE=pcb \\\n'
                   '       -DAFO_WIFI=1 -DAFO_DIAGNOSTIC_STAGE=0 -DAFO_IMU_COUNT=2 build'),
              p('`AFO_DIAGNOSTIC_STAGE` selects 2 (controller), 3 (ADC), 4/5 (analog) or 6 (IMU); diagnostics do not mount '
                'SD or start Wi-Fi. Use a separate build directory for each combination.')]

    # 8. Recording and data
    story += [Paragraph('8. Recording, live preview and data', ST['h1'])]
    story += bullets([
        'The button starts and stops a session. Recording is refused while USB is attached or the battery is low.',
        'Files keep the AFOLOG1 header and 64-byte CRC-protected records (schema 3, record kind 7 for AD7606 frames). '
        'Each EMG record carries both codes, read duration, elapsed slots, channel mask 0x03 and a read-start timestamp.',
        'The SD file is the primary record. Wi-Fi is a second, best-effort path: preview losses are shown and never '
        'alter the SD stream.',
        'Wait for the recording LED to go out before removing power or the card. An error LED, a nonzero stop reason '
        'or a missing END needs investigation.',
        'At first boot the recorder prints its Wi-Fi password on the USB console '
        '(`Laptop AP: AFO-Recorder-B; password: …`). Erasing flash creates a new one.',
    ])
    story += [Paragraph('Converting a recording', ST['h2']),
              code('python3 host/convert.py trial.afolog --out trial-csv --no-plots'),
              p('Output: `emg.csv`, `foot.csv`, `shank.csv`, `status.csv`, `metadata.json` and `quality.json`. Exit code 0 '
                'means the loss and signal checks passed; 2 means the output has reported quality problems; 1 means '
                'conversion failed. EMG values are volts at the RAW connector, not input-referred muscle microvolts. '
                'Live view: with USB removed, join `AFO-Recorder-B` and run '
                '`python3 host/live_receiver.py --device 192.168.4.1 --out trial-wifi`; the live page opens on port 8766.')]
    lp = D / 'live-preview.png'
    if lp.exists():
        story += [KeepTogether([figure_image(lp, 380), p('Laptop live preview (software replay, not a measurement).', 'small')]),
                  Spacer(1, 8)]

    # 9. Stages
    story += [Paragraph('9. Build sequence', ST['h1']),
              p('Build one stage at a time with power off for each addition, and record the result before continuing. '
                'An empty results cell means untested. No person is attached during any instrument-connected test.')]
    rows = [['Stage', 'Goal', 'Firmware', 'Pass when']]
    for s in data['stages']['stages']:
        acc = ' '.join('• ' + c['acceptance'] for c in s['checks'][:3])
        if len(s['checks']) > 3:
            acc += f" (+{len(s['checks']) - 3} more checks in the workbook)"
        rows.append([str(s['stage']), s['title'], s['firmware'], acc or s['actions']])
    story += table(rows, [38, 104, 100, W - 242])

    # 10. Evidence
    web = data['web']; au = data['audit']
    story += [Paragraph('10. Verification evidence', ST['h1']),
              p(f"**Wokwi integrated matrix on firmware {web['firmware']}: {web['passed_cases']} of "
                f"{web['planned_cases']} cases pass** ({web['engine']}, 12 October 2026). Each case runs the production "
                'recorder, sensor drivers, serializer and Wi-Fi task on an instrumented image; each serial export is '
                'checked with the production converter and live decoder, and each case keeps its logic-analyser trace.')]
    rows = [['Case', 'Result', 'Outcome']]
    for c in web['cases']:
        name = c['case'] if isinstance(c['case'], str) else str(c['case'])
        rows.append([CASE_TEXT.get(name, name), 'Pass' if c['pass'] else 'FAIL', case_outcome(c)])
    story += table(rows, [140, 40, W - 180])
    story += [Paragraph('Other checks', ST['h2'])]
    story += table([
        ['Check', 'Result'],
        ['KiCad ERC / DRC', '0 / 0 violations; no unconnected items'],
        ['Schematic vs PCB pads', '395 pins compared, 0 mismatches; firmware GPIO map matches'],
        ['Host tools', '48 converter, live-decoder, legacy and firmware-limit tests pass (rerun 12 October 2026)'],
        ['Native recorder control', '38 production-code cases (19 per board) pass'],
        ['Native drivers', '17 AD7606 driver groups and 9 IMU timing groups pass (ASan/UBSan)'],
        ['ICM register model', 'Production driver passes with no datasheet-rule violation; fault cases detected'],
        ['60 s native pipeline', '480,000 EMG frames, 12,009 foot, 12,001 shank; no unexplained loss'],
        ['ngspice analog', 'Both channels, 16 tolerance corners, 54 DC/loading cases'],
        ['Physical tests', 'None performed'],
    ], [140, W - 140])
    story += [p('These scopes are distinct and none is a measurement of an assembled recorder. Earlier failed and '
                'partial runs (1.11, v1.5) are kept in the repository rather than relabelled.')]

    # 11. Open items
    story += [Paragraph('11. Open items before use', ST['h1'])]
    story += bullets([
        'Qualify the received AD7606 module electrically (serial strap, VIO routing, reference) before connecting it.',
        'Measure every rail, start-up and ripple (stage 1), including the 5 V ADC rail never exceeding 5.25 V.',
        'Measure actual 8 kHz trigger timing and jitter under SD and Wi-Fi load; the 125 µs budget is only arithmetic so far.',
        'Measure analog noise, clipping and crosstalk; set study-specific limits before claiming research suitability.',
        'Characterise each IMU clock (200 Hz and µs-per-tick within ±2 %) and EMG-to-IMU alignment.',
        'Run a 60-minute SD endurance recording and the full-card and power-cut recovery checks.',
        'Measure battery runtime (target at least two hours) and 20 repeatable start/stop cycles.',
        'Complete the final PCB layout review before ordering, then repeat power, ripple, antenna, thermal and noise '
        'checks on the built board.',
        'Obtain institutional review before any wearable or participant use. Engineering stage completion does not '
        'authorise participants.',
    ])

    # 12. File map
    story += [Paragraph('12. Where things are', ST['h1'])]
    story += table([
        ['Path (inside designs/ad7606-two-channel-icm42688/)', 'Contents'],
        ['development/index.html', 'Stage-by-stage workbook with blank results sheets'],
        ['viewer/build.html', 'Interactive assembly workspace (serve over HTTP)'],
        ['docs/build-guide.html', 'Complete hole/contact connection tables'],
        ['docs/lab-quickstart.html', 'Short lab sequence with pass limits and diagnostic field meanings'],
        ['docs/circuit-audit.html', 'Circuit review, datasheet cross-checks and the supply-ramp change'],
        ['docs/integrated-verification.html', 'Wokwi matrix report and history'],
        ['docs/understanding-the-recorder.pdf', 'Longer supervisor handbook (background and study design)'],
        ['docs/circuit-diagrams.pdf', 'Functional map and full KiCad schematic'],
        ['firmware/builds/', 'Nine profiles with manifests and hashes'],
        ['hardware/, manufacturing/', 'KiCad sources; Gerber, drill, BOM, placement and STEP exports'],
        ['host/', 'Converter, live receiver, plots and tests'],
        ['breadboard/breadboard-lab-kit.zip', 'Self-contained lab kit for the breadboard stages'],
    ], [220, W - 220], mono_cols=(0,))
    story += [p('Live project: https://shadowfax-505.github.io/afo-recorder/ · Source: '
                'https://github.com/shadowfax-505/afo-recorder')]

    Doc(OUT).multiBuild(story)
    from pypdf import PdfReader
    print(OUT.relative_to(P), len(PdfReader(OUT).pages), 'pages')


if __name__ == '__main__':
    build()
