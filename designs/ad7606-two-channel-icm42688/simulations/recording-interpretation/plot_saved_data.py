#!/usr/bin/env python3
"""Plot existing captured CSV values; never generate replacement measurements."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P = Path(__file__).resolve().parent
RUN = P.parent / 'integrated-recorder/results/web-current/filtered-synthetic-emg/converted'


def rows(name):
    with (RUN / f'{name}.csv').open() as f: return list(csv.DictReader(f))


def main():
    emg, foot, shank = rows('emg'), rows('foot'), rows('shank')
    t0 = int(emg[0]['conversion_trigger_host_us'])
    t = [(int(r['conversion_trigger_host_us']) - t0) / 1e6 for r in emg]
    colors = ['#087e8b', '#b95b19']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(3, 1, figsize=(11.2, 8.2), layout='constrained')
    fig.suptitle('Saved data, decoded from the running recorder\nSynthetic Wokwi inputs · AD7606 / two EMG / ICM-42688-P',
                 fontsize=15, fontweight='bold')
    for i in range(2):
        values = [float(r[f'ch{i}_adc_input_v']) for r in emg]
        axes[0].plot(t, values, color=colors[i], lw=.8, label=f'EMG{i + 1} ADC input')
        axes[1].plot(t[:480], values[:480], color=colors[i], lw=1.15, label=f'EMG{i + 1}')
    axes[0].set(ylabel='Voltage (V)', title='Entire saved waveform test: 10,041 simultaneous frames')
    axes[1].set(ylabel='Voltage (V)', xlabel='Time since first EMG trigger (s)', title='First 60 ms: channel identity and waveform detail')
    axes[0].legend(loc='upper right', ncols=2)
    for values, name, color, marker in [(foot, 'Foot', colors[0], 'o'), (shank, 'Shank', colors[1], 'x')]:
        times = [(int(r['host_time_estimate_us']) - t0) / 1e6 for r in values]
        axes[2].plot(times, [float(r['az_g']) for r in values], color=color, marker=marker,
                     markevery=13, ms=4, lw=.75, label=f'{name} z acceleration')
    axes[2].set(ylabel='Acceleration (g)', xlabel='Estimated host time relative to first EMG trigger (s)',
                ylim=(.96, 1.04), title='Both modeled IMUs are stationary at 1 g; all host times are marked uncertain')
    axes[2].legend(ncols=2, loc='upper right')
    for ax in axes: ax.grid(alpha=.15)
    fig.text(.01, -.025, 'Precomputed ngspice voltages feed the ADC model. No person, real MyoWare signal or physical SD card is represented.',
             fontsize=9, color='#475569')
    for extension in ['png', 'svg']:
        fig.savefig(P / f'saved-signals.{extension}', dpi=160, bbox_inches='tight',
                    metadata={'Date': None} if extension == 'svg' else None)
    plt.close(fig)


if __name__ == '__main__': main()
