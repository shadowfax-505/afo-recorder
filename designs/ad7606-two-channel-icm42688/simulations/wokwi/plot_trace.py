#!/usr/bin/env python3
"""Render the first measured conversion from a Wokwi VCD, using Matplotlib."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re

def plot(vcd, output):
    ids={};state={};t=0;first=None;events=[[] for _ in range(5)]
    with Path(vcd).open() as stream:
        for line in stream:
            line=line.strip();m=re.match(r'\$var\s+\S+\s+1\s+(\S+)\s+D([0-4])\b',line)
            if m:ids[m[1]]=int(m[2]);continue
            if re.fullmatch(r'#\d+',line):t=int(line[1:])
            elif len(line)>1 and line[0] in '01' and line[1:] in ids:
                c=ids[line[1:]];v=int(line[0]);old=state.get(c);state[c]=v
                if c==0 and v and old==0 and t>0 and first is None:
                    first=t
                    for i in range(5):events[i].append((0,state.get(i,0)))
                if first is not None:events[c].append(((t-first)/1000,v))
            if first is not None and t-first>40000:break
    if first is None:raise ValueError('No conversion trigger captured')
    colors=['#176d65','#ae7014','#675098','#37495f','#2073a6'];labels=['CONVST','BUSY','CS','SCLK','DOUTA']
    fig,axs=plt.subplots(5,1,figsize=(11,5.2),sharex=True)
    for i,ax in enumerate(axs):
        points=events[i]+[(40,events[i][-1][1])];x,y=zip(*points)
        ax.step(x,y,where='post',color=colors[i],lw=1.5);ax.set_ylim(-.25,1.25)
        ax.set_yticks([0,1]);ax.set_ylabel(labels[i],rotation=0,labelpad=35,va='center',fontsize=10)
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.2)
    axs[-1].set_xlabel('Time after first CONVST rising edge (µs)');axs[-1].set_xlim(0,40)
    fig.suptitle('AD7606 — first acquisition after SPI initialization',x=.12,ha='left',fontsize=15)
    fig.text(.12,.015,'Wokwi ESP32-S3 + behavioral ADC model • virtual logic trace • no physical measurements',fontsize=9,color='#586462')
    fig.tight_layout(rect=[.04,.04,1,.94]);output=Path(output);output.parent.mkdir(exist_ok=True)
    fig.savefig(output.with_suffix('.svg'));fig.savefig(output.with_suffix('.png'),dpi=160);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('vcd');p.add_argument('output');a=p.parse_args();plot(a.vcd,a.output)
