"""Generate solid STEP package envelopes using CadQuery, not vendor detailed CAD."""
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'hardware'/'models';out.mkdir(exist_ok=True)
for name,w,d,h in [('TPS63070_envelope',2.5,3,1),('ASE_envelope',3.2,2.5,1.2),('JS102011_envelope',8.6,4.3,4)]:
    shape=cq.Workplane('XY').box(w,d,h,centered=(True,True,False))
    cq.exporters.export(shape,str(out/(name+'.step')))
    assert shape.val().isValid()
    print(name,shape.val().Volume())
