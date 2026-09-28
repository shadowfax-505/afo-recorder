"""Export actual KiCad pad and track geometry for viewer/net consistency checks."""
import pcbnew as k,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for name in ['main']:
 s=json.loads((ROOT/'design'/f'{name}.json').read_text());b=k.LoadBoard(str(ROOT/'hardware'/name/f'afo_revb_{name}.kicad_pcb'));byref={p['ref']:p for p in s['parts']}
 for f in b.GetFootprints():
  p=byref[f.GetReference()];p['pads']=[dict(pin=pad.GetNumber(),net=pad.GetNetname(),x=k.ToMM(pad.GetPosition().x),y=k.ToMM(pad.GetPosition().y)) for pad in f.Pads() if pad.GetNumber()]
 s['tracks']=[dict(net=t.GetNetname(),layer=b.GetLayerName(t.GetLayer()),width=k.ToMM(t.GetWidth()),a=[k.ToMM(t.GetStart().x),k.ToMM(t.GetStart().y)],b=[k.ToMM(t.GetEnd().x),k.ToMM(t.GetEnd().y)],via=isinstance(t,k.PCB_VIA)) for t in b.GetTracks()]
 (ROOT/'viewer'/f'{name}.json').write_text(json.dumps(s,separators=(',',':')))
 print(name,len(s['tracks']),'copper elements')
