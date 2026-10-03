"""Export and plot observed first-two-frame edges, without inventing a full trace."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re

from assess_probe import SIGNALS, entries, normalize_console


def export(directory, plots=True):
    directory = Path(directory)
    source = directory / 'chips-console.txt'
    text = normalize_console(source.read_text())
    initial = entries(text, 'PROBE_INITIAL')[0]
    baseline = initial['time_ns']
    rows = [(baseline, name, value, 'initial_snapshot')
            for name, value in zip(SIGNALS, initial['levels'])]
    rows += [(int(t), name, int(v), 'observed_edge') for t, name, v in
             re.findall(r'PROBE_EDGE,(\d+),([A-Z0-9_]+),([01])(?:\r?$|\n)', text, re.M)]
    with (directory / 'sampled-edges.csv').open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['virtual_time_ns', 'relative_time_ns', 'signal', 'logic_value', 'source'])
        writer.writerows((t, t - baseline, name, v, origin) for t, name, v, origin in rows)
    ids = {name: chr(33 + i) for i, name in enumerate(SIGNALS)}
    vcd = ['$version Derived from actual Wokwi input-only pin observer $end',
           '$comment Partial capture: first two ADC reads and a leading BUSY edge of the next conversion. '
           'Not a downloaded full-session logic-analyzer VCD; no physical measurements. $end',
           '$timescale 1ns $end', '$scope module virtual_probe $end']
    vcd += [f'$var wire 1 {identity} {name} $end' for name, identity in ids.items()]
    vcd += ['$upscope $end', '$enddefinitions $end']
    for t, name, value, _ in rows:
        vcd.extend([f'#{t - baseline}', f'{value}{ids[name]}'])
    (directory / 'sampled-edges.vcd').write_text('\n'.join(vcd) + '\n')
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plotted = ['CONVST', 'BUSY', 'CS', 'SCLK', 'DOUTA']
        frames = entries(text, 'PROBE_FRAME')
        first_cs = (frames[0]['cs_start_ns'] - baseline) / 1000
        colors = ['#236a62', '#ae6939', '#526f83', '#4a6254', '#785b84']
        with plt.rc_context({'font.family': 'DejaVu Sans', 'font.size': 10,
                             'axes.spines.top': False, 'axes.spines.right': False}):
            fig, axes = plt.subplots(2, 1, figsize=(11, 6.6), layout='constrained')
            for ax in axes:
                for index, (name, color) in enumerate(zip(plotted, colors)):
                    data = [(t, v) for t, signal, v, _ in rows if signal == name]
                    x = [(t - baseline) / 1000 for t, _ in data]
                    y = [(len(plotted) - 1 - index) * 1.2 + .65 * v for _, v in data]
                    ax.step(x, y, where='post', color=color, linewidth=1.15)
                ax.set_yticks([i * 1.2 + .325 for i in range(len(plotted))], list(reversed(plotted)))
                ax.set_ylim(-.25, len(plotted) * 1.2)
                ax.grid(axis='x', color='#dddddd', linewidth=.6)
                ax.set_xlabel('Virtual time after first observed CONVST (µs)')
            axes[0].set_xlim(0, 35)
            axes[0].set_title('First ADC read: BUSY completes before 128 falling-edge data clocks', loc='left', fontweight='bold')
            axes[0].axvspan(0, 4, color=colors[1], alpha=.08)
            axes[0].text(1, 5.75, 'BUSY: 4 µs', color=colors[1], fontsize=9)
            axes[0].text(first_cs + 2, 5.75, 'SPI transaction: 16 µs', fontsize=9)
            axes[1].set_xlim(first_cs - .15, first_cs + 4.15)
            axes[1].set_title('Read-clock detail: 125 ns between sample edges (8 MHz)', loc='left', fontweight='bold')
            fig.suptitle('Actual Wokwi pin observation — AD7606 / two EMG / ICM-42688-P', x=.08,
                         ha='left', fontsize=14, fontweight='bold')
            fig.supxlabel('Input-only project probe · partial edge capture · simulation, not bench measurements', fontsize=9)
            fig.savefig(directory / 'adc-timing.png', dpi=160)
            fig.savefig(directory / 'adc-timing.svg')
            plt.close(fig)
    names = ['sampled-edges.csv', 'sampled-edges.vcd']
    if plots: names += ['adc-timing.png', 'adc-timing.svg']
    manifest = {'hardware_measured': False, 'source': source.name,
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'coverage': 'First two complete ADC reads; final edge is BUSY rising before the third CONVST callback',
                'observed_edge_count': len(rows) - len(SIGNALS), 'initial_snapshot_values': len(SIGNALS),
                'full_session_vcd_qualified': False,
                'sha256': {n: hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in names}}
    (directory / 'edge-exports.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    print(json.dumps(export(args.directory, plots=not args.no_plots), indent=2))
