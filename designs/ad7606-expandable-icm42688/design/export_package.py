"""Export manufacturing prototypes and review drawings from checked KiCad sources."""
import subprocess,json,csv,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def export(n):
 h=ROOT/'hardware'/n;p=h/f'afo_revb_{n}.kicad_pcb';out=ROOT/'manufacturing'/n;out.mkdir(parents=True,exist_ok=True)
 def run(args):
  r=subprocess.run([CLI]+list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  with (out/'export.log').open('a') as f:f.write(' '.join(map(str,args))+'\n'+r.stdout+'\n')
  if r.returncode:raise RuntimeError((n,args[0:3],r.stdout[-1000:]))
 (out/'export.log').write_text('ENGINEERING PROTOTYPE — pending physical validation and assembly review\n')
 layers='F.Cu,B.Cu,'+('In1.Cu,In2.Cu,' if n!='imu' else '')+'F.Paste,B.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts'
 run(['pcb','export','gerbers','--layers',layers,'-o',str(out/'gerbers')+'/',p])
 run(['pcb','export','drill','--format','excellon','--generate-map','--map-format','svg','-o',str(out/'drill')+'/',p])
 run(['pcb','export','pos','--format','csv','--units','mm','--side','both','-o',out/'placement.csv',p])
 run(['pcb','export','svg','--layers','F.Fab,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--sketch-pads-on-fab-layers','-o',out/'assembly.svg',p])
 run(['sch','export','netlist','--format','kicadxml','-o',h/'netlist.xml',h/f'afo_revb_{n}.kicad_sch'])
 run(['sch','export','svg','-o',str(out/'schematic')+'/',h/f'afo_revb_{n}.kicad_sch'])
 spec=json.loads((ROOT/'design'/f'{n}.json').read_text())
 with (out/'bom.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['Reference','Value','MPN','Footprint','Assembly'])
  for c in spec['parts']:w.writerow([c['ref'],c['value'],c['mpn'],c['footprint'],'Copper only' if c['ref'].startswith('TP') else 'Mechanical' if not c['pins'] else 'Populate'])
 run(['pcb','export','step','--subst-models','--force','-o',out/f'afo_revb_{n}.step',p])
 run(['pcb','export','glb','--subst-models','--include-tracks','--include-pads','--force','-o',ROOT/'viewer'/f'{n}.glb',p])
 return n
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
  for n in ex.map(export,['main']):print('Exported',n,flush=True)
