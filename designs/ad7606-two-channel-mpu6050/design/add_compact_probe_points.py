"""Expose existing through vias as numbered backside probe lands, without routing stubs.
Idempotent: run only after routing. Does not change any functional net.
"""
import pcbnew as k,json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'hardware/main/afo_revb_main.kicad_pcb';b=k.LoadBoard(str(path))
wanted=['GND','VBAT','3V3D','3V0A','VMID','5V_ADC','ADC_DRDY','ADC_SCK','ADC_MISO','ADC_CONVST','USB_PRESENT_N','BAT_SENSE']+[f'BUF{i}{s}' for i in range(2) for s in ['A','B']]
rows=[]
# Existing vias are already accessible on both board faces. Number the locations
# on the fabrication layer, avoiding extra pads/capacitance on clock nets.
for i,net in enumerate(wanted,1):
 vias=[t for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net]
 if not vias:
  pads=[(f,p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname()==net]
  f,p=pads[0];pos=p.GetPosition();location=f.GetReference()+'.'+p.GetNumber();side='F.Cu';kind='existing component pad; microprobe'
 else:
  v=vias[0];pos=v.GetPosition();location='via';side='B.Cu';kind='existing via; microprobe'
 label=f'TP{i:02d} {net}'
 existing=next((d for d in b.GetDrawings() if isinstance(d,k.PCB_TEXT) and d.GetText()==label),None)
 if existing is not None:
  existing.SetPosition(pos);existing.SetLayer(k.B_Fab if side=='B.Cu' else k.F_Fab);existing.SetMirrored(side=='B.Cu')
 else:
  t=k.PCB_TEXT(b);t.SetText(label);t.SetPosition(pos);t.SetTextSize(k.VECTOR2I(k.FromMM(.6),k.FromMM(.6)));t.SetTextThickness(k.FromMM(.1));t.SetLayer(k.B_Fab if side=='B.Cu' else k.F_Fab);t.SetMirrored(side=='B.Cu');b.Add(t)
 rows.append([f'TP{i:02d}',net,k.ToMM(pos.x),k.ToMM(pos.y),side,location,kind])
k.SaveBoard(str(path),b)
with (ROOT/'design/compact-probe-points.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['ID','Net','X_mm','Y_mm','Side','Contact','Method']);w.writerows(rows)
