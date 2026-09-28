#!/usr/bin/env python3
"""Actual ngspice analysis with explicitly substituted closed-loop buffer models."""
from pathlib import Path
import itertools,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ngspice_runner import Spice
HERE=Path(__file__).resolve().parent
MODEL='''
* Substitute closed-loop MCP600x approximation: 1 MHz pole, 1 ohm output,
* 20mV assumed rail headroom. NOT a manufacturer macromodel.
* Omits noise, bias/offset, current/slew limiting, PSRR, temperature and stability.
.subckt buffer inp out
Ein sense 0 inp 0 1
Rbw sense pole 1k
Cbw pole 0 159.154943p
Blimit driver 0 V=min(max(V(pole),0.02),2.98)
Ro driver out 1
.ends
'''
def circuit(r1=3300,c1=47e-9,r2=6650,rm=6650,c2=47e-9,transient=False):
 lines=['Revision B four-channel analog model','VDD avdd 0 3','VMID mid 0 1.5',MODEL]
 for i in range(4):
  source=f'Braw{i} raw{i} 0 V=1.5+0.4*(1+0.3*sin(2*pi*2*time))*sin(2*pi*{71+23*i}*time)+0.07*sin(2*pi*50*time)+0.05*sin(2*pi*6500*time)' if transient else f'Vin{i} raw{i} 0 DC 1.5 AC 1'
  lines += [source,f'Rb{i} raw{i} mid 1Meg',f'Ra{i} raw{i} a{i} {r1}',f'Ca{i} a{i} 0 {c1}',f'Xa{i} a{i} ba{i} buffer',f'Rmix{i} ba{i} mix{i} {r2}',f'Rmid{i} mid mix{i} {rm}',f'Cb{i} mix{i} 0 {c2}',f'Xb{i} mix{i} bb{i} buffer',f'Rp{i} bb{i} p{i} 100',f'Rn{i} mid n{i} 100',f'Cd{i} p{i} n{i} 1n',f'Rload{i} p{i} n{i} 330k']
 return '\n'.join(lines+['.end'])+'\n'
def main():
 out=HERE/'results';out.mkdir(exist_ok=True);sp=Spice();net=circuit();(HERE/'analog_nominal.cir').write_text(net);sp.circuit(net);sp.command('ac dec 60 1 100000')
 f=sp.vector('frequency').real;h=sp.vector('v(p0)')-sp.vector('v(n0)');w=2*np.pi*f
 # Includes both one-ohm buffer outputs and 330k ADC differential input loading.
 ideal=.5/(1+1j*w*3300*47e-9)/(1+1j*w*3325*47e-9)/(1+1j*f/1e6)**2/(1+201/330000+1j*w*201e-9)
 error=float(np.max(np.abs(20*np.log10(abs(h[f<20000]/ideal[f<20000])))))
 assert error<.02,error
 for i in range(1,4):assert np.max(np.abs((sp.vector(f'v(p{i})')-sp.vector(f'v(n{i})'))-h))<1e-8
 corners=[]
 for signs in itertools.product((-1,1),repeat=5):
  vals=[3300*(1+signs[0]*.01),47e-9*(1+signs[1]*.10),6650*(1+signs[2]*.01),6650*(1+signs[3]*.01),47e-9*(1+signs[4]*.10)]
  sp.circuit(circuit(*vals));sp.command('ac dec 60 1 100000');corners.append(20*np.log10(abs(sp.vector('v(p0)')-sp.vector('v(n0)'))))
 db=20*np.log10(abs(h));phase=np.unwrap(np.angle(h));delay=-np.gradient(phase,w)*1e6;corners=np.array(corners)
 np.savetxt(out/'response.csv',np.c_[f,db,phase*180/np.pi,delay,corners.min(0),corners.max(0)],delimiter=',',header='Hz,gain_dB,phase_deg,group_delay_us,min_dB,max_dB',comments='')
 fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,constrained_layout=True)
 axs[0].fill_between(f,corners.min(0),corners.max(0),alpha=.3,label='32 R/C tolerance corners');axs[0].semilogx(f,db,label='ngspice nominal');axs[0].legend();axs[0].set_ylabel('Gain (dB)')
 axs[1].semilogx(f,phase*180/np.pi);axs[1].set_ylabel('Phase (degrees)');axs[2].semilogx(f,delay);axs[2].set_ylabel('Group delay (µs)');axs[2].set_xlabel('Frequency (Hz)')
 for a in axs:a.grid(alpha=.2)
 fig.suptitle('Revision B analog simulation · surrogate buffers · four identical paths');fig.savefig(out/'frequency-response.png',dpi=150);plt.close(fig)
 net=circuit(transient=True);(HERE/'analog_transient.cir').write_text(net);sp.circuit(net);sp.command('tran 2u .15 0 2u');t=sp.vector('time');sample_t=np.arange(.05,.15,1/8000)
 diff=np.array([np.interp(sample_t,t,sp.vector(f'v(p{i})')-sp.vector(f'v(n{i})')) for i in range(4)]).T
 code=np.clip(np.rint(diff/1.2*8388608),-8388608,8388607).astype(int);recon=code*1.2/8388608
 assert np.max(abs(recon-diff))<=1.2/8388608/2+1e-12
 np.savetxt(out/'ideal-adc-samples.csv',np.c_[sample_t,diff,code],delimiter=',',header='time_s,ch0_v,ch1_v,ch2_v,ch3_v,ch0_code,ch1_code,ch2_code,ch3_code',comments='')
 fig,axs=plt.subplots(2,1,figsize=(10,6),constrained_layout=True)
 for i in range(4):axs[0].plot(sample_t,diff[:,i],lw=.7,label=f'EMG{i+1}')
 axs[0].set(xlabel='Time (s)',ylabel='Differential ADC input (V)');axs[0].legend()
 stress=np.linspace(-1.5,1.5,500);q=np.clip(np.rint(stress/1.2*8388608),-8388608,8388607);axs[1].plot(stress,q);axs[1].set(xlabel='Hypothetical differential input (V)',ylabel='Signed 24-bit code');fig.suptitle('Synthetic signals and ideal ADC quantization/clipping, no hardware execution');fig.savefig(out/'transient-clipping.png',dpi=150);plt.close(fig)
 summary=dict(engine='ngspice shared library',analytical_max_error_db=error,tolerance_corners=32,resistor_tolerance_percent=1,filter_capacitor_tolerance_percent=10,all_four_channels_match=True,quantization_error_v=float(np.max(abs(recon-diff))),nominal_raw_input_range_v=[0,3],nominal_adc_diff_range_v=[-.75,.75],adc_full_scale_v=1.2,model='Substitute 1MHz closed-loop buffers; not vendor MCP6004 model',myoware='Synthetic RAW output waveform; no validated MyoWare or physiological model',limitations=['No op-amp noise, offset, slew/current limit or PSRR; shared midpoint is ideal so crosstalk is not validated.','330k resistive ADC loading approximation; switched-capacitor transients and sinc3 response are not simulated in ngspice.','ADC quantization is an ideal separate software model; 24-bit word width does not imply 24 effective bits.','Rail clamps and ESD are not validated by this linear operating-range model.','Supply/reference ripple and battery runtime require physical tests.'])
 (out/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
