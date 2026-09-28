"""Import a routed Specctra session, add ground fills, and save KiCad sources."""
import pcbnew as k,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
name=sys.argv[1];file=ROOT/'hardware'/name/('afo_revb_'+name+'.kicad_pcb');b=k.LoadBoard(str(file))
for z in list(b.Zones()):b.Remove(z)
assert k.ImportSpecctraSES(b,sys.argv[2]),'SES import failed'
for layer in ([k.In1_Cu] if name=='main' else [k.B_Cu]):
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(k.FromMM(.2));z.SetThermalReliefGap(k.FromMM(.25));z.SetThermalReliefSpokeWidth(k.FromMM(.25));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
 o=z.Outline();o.NewOutline();w,h=(75,50) if name=='main' else (20,20)
 for x,y in [(.3,.3),(w-.3,.3),(w-.3,h-.3),(.3,h-.3)]:o.Append(k.FromMM(x),k.FromMM(y))
 b.Add(z)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(file),b);print('Saved',file)
