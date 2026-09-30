#!/usr/bin/env python3
"""Couple the selected two-channel ngspice filter model to a virtual AD7606."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent))
from ngspice_runner import Spice

def main():
    circuit=(P.parent/'analog_transient.cir').read_text()
    spice=Spice();spice.circuit(circuit);spice.command('tran 2u 1.1')
    time=spice.vector('time');points=.1+np.arange(8000)/8000
    volts=np.vstack([np.interp(points,time,spice.vector(f'v(p{i})')) for i in range(2)])
    codes=np.clip(np.rint(volts*32768/5),-32768,32767).astype(np.int16)
    out=P/'stimulus';out.mkdir(exist_ok=True)
    (out/'analog-input.cir').write_text(circuit)
    with (out/'filtered-samples.csv').open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['index','time_s','emg1_v','emg2_v','code1','code2'])
        for i in range(8000):writer.writerow([i,points[i],*volts[:,i],*map(int,codes[:,i])])
    header=['// Synthetic ngspice output, not measured MyoWare data.','#pragma once','#include <stdint.h>',
            '#define STIMULUS_SAMPLES 8000','static const int16_t emg_stimulus[2][STIMULUS_SAMPLES] = {']
    for channel in codes:
        header.append('{')
        header.extend(','.join(map(str,channel[start:start+32]))+',' for start in range(0,8000,32))
        header.append('},')
    header.append('};')
    (P/'chips/stimulus.h').write_text('\n'.join(header)+'\n')
    report={'synthetic':True,'engine':'ngspice shared library','library':spice.path,
        'input':'Synthetic MyoWare RAW-like voltages; not a MyoWare circuit model',
        'analog':'Two 3.3k/47nF buffered poles, 100R/1nF output, 1Meg ADC loading',
        'buffer':'Substitute 1MHz/1ohm/20mV-headroom unity buffer; not manufacturer MCP6004 model',
        'adc':'Ideal signed 16-bit quantization, +/-5V, zero offset; no measured ADC errors',
        'samples':8000,'nominal_hz':8000,'loop_period_s':1,
        'voltage_range':[[float(np.min(ch)),float(np.max(ch))] for ch in volts],
        'max_quantization_error_v':float(np.max(abs(codes.astype(float)*5/32768-volts))),
        'circuit_sha256':hashlib.sha256(circuit.encode()).hexdigest(),
        'samples_sha256':hashlib.sha256((out/'filtered-samples.csv').read_bytes()).hexdigest(),
        'physical_measurements':False,
        'limits':['No electrode/body model','No measured noise, offset, reference drift, PSRR or thermal behavior',
                  'Wokwi receives precomputed codes; analog integration is offline, not a live mixed-signal simulator']}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
