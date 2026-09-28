"""Run with KiCad bundled Python (pcbnew). Generates editable engineering sources.
Do not regenerate after manual routing without saving the routed board separately.
"""
import json,math,uuid,csv
from pathlib import Path
import pcbnew as k
ROOT=Path(__file__).resolve().parents[1]
LIB=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
def mm(v):return k.FromMM(v)
def xy(x,y):return k.VECTOR2I(mm(x),mm(y))
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'afo-revb/'+s))
def q(s):return json.dumps(str(s))
def custom():
    d=ROOT/'hardware'/'RevB.pretty';d.mkdir(exist_ok=True)
    pads=[]
    for n,y in enumerate([-.75,-.25,.25,.75],1):pads.append((n,-1.15,y,.6,.25))
    for n,x in [(5,-.725),(6,-.225),(7,.275),(8,.775)]:pads.append((n,x,1.4,.25,.6))
    for n,x in [(15,-.725),(14,-.225),(13,.275),(12,.775)]:pads.append((n,x,-1.4,.25,.6))
    pads += [(9,.775,.5,1.35,.25),(10,.6,0,1.7,.25),(11,.775,-.5,1.35,.25)]
    s='(footprint "TI_RNM0015A" (version 20250108) (generator "pcbnew") (layer "F.Cu") (attr smd)'
    s+='(descr "TPS63070 TI RNM0015A; pad centers from drawing 4222000/B. Assembly review required.")'
    for n,x,y,w,h in pads:
        if 7<=n<=13:w+=.1;h+=.1
        s+=f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask") (roundrect_rratio .1)'+(' (solder_mask_margin -.05) (solder_paste_margin_ratio -.04)' if 7<=n<=13 else ' (solder_mask_margin .05)')+')'
    for layer,size in [('F.Fab',(1.25,1.5)),('F.CrtYd',(1.75,1.95))]:
        a,b=size;s+=f'(fp_rect (start {-a} {-b}) (end {a} {b}) (stroke (width .05) (type default)) (fill none) (layer "{layer}"))'
    s+='(fp_circle (center -1.7 -.75) (end -1.6 -.75) (stroke (width .12) (type default)) (fill none) (layer "F.SilkS")))'
    (d/'TI_RNM0015A.kicad_mod').write_text(s)
def schematic(spec):
    name='afo_revb_'+spec['board'];rootid=uid(name);out=ROOT/'hardware'/spec['board'];out.mkdir(exist_ok=True)
    libs=[];items=[];groups={}
    for p in spec['parts']:groups.setdefault(p['section'],[]).append(p)
    positions={};rowy=25
    # Functional groups on a single large, zoomable sheet; all connections are named.
    for group,ps in groups.items():
        items.append(f'(text {q(group.upper())} (at 20 {rowy} 0) (effects (font (size 2.5 2.5)) (justify left)) (uuid {uid(name+group)}))')
        rowy+=12;rowheight=0
        for i,p in enumerate(ps):
            if i%8==0 and i:rowy+=rowheight+15;rowheight=0
            n=len(p['pins']);height=max(15,math.ceil(n/2)*2.54+12);rowheight=max(rowheight,height)
            positions[p['ref']]=(75+(i%8)*135,rowy+height/2)
        rowy+=rowheight+24
    for p in spec['parts']:
        ref=p['ref'];pins=list(p['pins']);sid=uid(name+'/'+ref);lid='RevB:'+ref;x,y=positions[ref];x=round(x/1.27)*1.27;y=round(y/1.27)*1.27
        count=math.ceil(len(pins)/2);half=max(5,(count-1)*1.27+2.54)
        pintext='';pincoords=[]
        for i,n in enumerate(pins):
            left=i<count;px=-22.86 if left else 22.86;py=((count-1)/2-(i if left else i-count))*2.54;angle=0 if left else 180
            net=p['pins'][n];label=p['names'].get(n,net or 'NC');kind='passive'
            if ref.startswith('U'):
                if label in ['NC']:kind='no_connect'
                elif net and net.replace('_SOURCE','') in ['GND','3V3D','3V0A','3V3','VBAT']:kind='power_in'
                else:kind='bidirectional'
            if spec.get('electrical_role',spec['board'])=='main' and ref=='U6' and n=='7':kind='power_out'
            if spec.get('electrical_role',spec['board'])=='main' and ref=='U7' and n=='5':kind='power_out'
            if spec.get('electrical_role',spec['board'])=='main':
                if ref in ['U3','U4'] and n not in ['4','11']:kind='output' if n in ['1','7','8','14'] else 'input'
                if ref=='U5' and n in ['1','3','4']:kind='output' if n=='1' else 'input'
                if ref=='U2' and n not in ['1','2','19','20']:kind='output' if n in ['13','15'] else 'power_out' if n=='18' else 'input'
                if ref=='U1' and net not in ['GND','3V3D',None]:
                    kind='input' if net in ['EN','BOOT','BUTTON','ADC_MISO','ADC_DRDY','IMU_RESERVED','FOOT_INT','SHANK_INT','USB_PRESENT_N','BAT_SENSE','UART_RX'] else 'bidirectional' if net in ['USB_DM_MCU','USB_DP_MCU','SD_CMD','SD_D0','EXP_SDA','EXP_SCL'] else 'output'
                if ref=='U6' and n in ['1','14','15','5']:kind='input'
                if ref=='U6' and n=='3':kind='power_out'
                if ref=='U6' and n=='2':kind='open_collector'
                if ref=='U7' and n=='3':kind='input'
            elif ref=='U1':
                kind={'1':'tri_state','4':'output','5':'power_in','6':'power_in','8':'power_in','9':'input','12':'input','13':'input','14':'input'}.get(n,'passive')
            pintext+=f'(pin {kind} line (at {px} {py} {angle}) (length 5.08) (name {q(label)} (effects (font (size .85 .85)))) (number {q(n)} (effects (font (size .8 .8)))))'
            pincoords.append((n,x+px,y-py,left))
        shape=f'(rectangle (start -17.78 {half}) (end 17.78 {-half}) (stroke (width .2) (type default)) (fill (type background)))'
        libs.append(f'(symbol {q(lid)} (pin_names (offset .5)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" {q(p["value"])} (at 0 0 0) (effects (font (size 1 1)))) (symbol {q(ref+"_0_1")} {shape}) (symbol {q(ref+"_1_1")} {pintext}))')
        props=''
        for i,(key,val) in enumerate([('Reference',ref),('Value',p['value']),('Footprint',p['footprint']),('MPN',p['mpn'])]):
            props+=f'(property {q(key)} {q(val)} (at {x} {y-half-5+i*2.54} 0) (effects (font (size 1 1))'+(' (hide yes)' if i>1 else '')+'))'
        items.append(f'(symbol (lib_id {q(lid)}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {sid}) {props} (instances (project {q(name)} (path "/{rootid}" (reference {q(ref)}) (unit 1)))))')
        for n,px,py,left in pincoords:
            net=p['pins'][n]
            if net is None:
                items.append(f'(no_connect (at {px} {py}) (uuid {uid(sid+n+"nc")}))');continue
            ex=px+(-3.81 if left else 3.81)
            items.append(f'(wire (pts (xy {px} {py}) (xy {ex} {py})) (stroke (width 0) (type default)) (uuid {uid(sid+n+"w")}))')
            items.append(f'(label {q(net)} (at {ex} {py} {0 if left else 180}) (effects (font (size .9 .9)) (justify {"left" if left else "right"} bottom)) (uuid {uid(sid+n+"l")}))')
    for i,net in enumerate(spec.get('power_flags', ['GND','VBAT'] if spec.get('electrical_role',spec['board'])=='main' else ['GND','3V3'])):
        fid='Flag'+str(i);sid=uid(name+fid);x=1117.6;y=round((40+i*15)/1.27)*1.27
        libs.append(f'(symbol "RevB:{fid}" (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)))) (property "Value" "PWR_FLAG" (at 0 0 0) (effects (font (size 1 1)))) (symbol "{fid}_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))')
        items.append(f'(symbol (lib_id "RevB:{fid}") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {sid}) (property "Reference" "#FLG0{i+1}" (at {x} {y-2.54} 0) (effects (font (size 1 1)))) (property "Value" "PWR_FLAG" (at {x} {y-5.08} 0) (effects (font (size 1 1)))) (instances (project {q(name)} (path "/{rootid}" (reference "#FLG0{i+1}") (unit 1)))))')
        items.append(f'(label {q(net)} (at {x} {y} 0) (effects (font (size 1 1)) (justify left bottom)) (uuid {uid(sid+"label")}))')
    (out/'RevB.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(v.replace('"RevB:', '"',1) for v in libs)+')')
    (out/'sym-lib-table').write_text('(sym_lib_table (lib (name "RevB") (type "KiCad") (uri "${KIPRJMOD}/RevB.kicad_sym") (options "") (descr "Revision B physical pin symbols")))')
    h=max(841,math.ceil((rowy+30)/10)*10)
    text=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid {rootid}) (paper "User" 1189 {h}) (title_block (title "AFO Revision B {spec["board"]}") (rev "B engineering prototype") (comment 1 "Named nets connect all matching labels; physical package pin numbers.")) (lib_symbols {"".join(libs)}) {"".join(items)} (embedded_fonts no))'
    (out/(name+'.kicad_sch')).write_text(text)
    return rootid

def board(spec):
    name='afo_revb_'+spec['board'];out=ROOT/'hardware'/spec['board'];rootid=schematic(spec)
    b=k.BOARD();b.SetCopperLayerCount(4 if spec.get('electrical_role',spec['board'])=='main' else 2)
    ds=b.GetDesignSettings();ds.m_MinClearance=mm(.15);ds.m_TrackMinWidth=mm(.15);ds.m_ViasMinSize=mm(.5);ds.m_CopperEdgeClearance=mm(.3)
    nets={n:k.NETINFO_ITEM(b,n) for n in sorted({v for p in spec['parts'] for v in p['pins'].values() if v})}
    for n in nets.values():b.Add(n)
    missing=[]
    for p in spec['parts']:
        lib,fp=p['footprint'].split(':');path=ROOT/'hardware'/'RevB.pretty' if lib=='RevB' else LIB/(lib+'.pretty')
        f=k.FootprintLoad(str(path),fp)
        if not f:raise RuntimeError('Missing footprint '+p['footprint'])
        f.SetReference(p['ref']);f.SetValue(p['value']);f.SetFPID(k.LIB_ID(lib,fp));f.SetPosition(xy(p['x'],p['y']));f.SetOrientationDegrees(p['rotation'])
        f.SetPath(k.KIID_PATH('/'+rootid+'/'+uid(name+'/'+p['ref'])))
        f.Value().SetVisible(False);f.Reference().SetLayer(k.F_Fab);f.Reference().SetTextSize(xy(1,1));f.Reference().SetTextThickness(mm(.15))
        actual={pad.GetNumber() for pad in f.Pads() if pad.GetNumber()}
        for num in p['pins']:
            if num not in actual:missing.append(p['ref']+'.'+num)
        for pad in f.Pads():
            n=p['pins'].get(pad.GetNumber())
            if n:pad.SetNet(nets[n])
        b.Add(f)
    if missing:raise RuntimeError('Specified pins missing from footprints: '+str(missing))
    w=spec['width_mm'];h=spec['height_mm']
    for a,z in [((0,0),(w,0)),((w,0),(w,h)),((w,h),(0,h)),((0,h),(0,0))]:
        s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(xy(*a));s.SetEnd(xy(*z));s.SetLayer(k.Edge_Cuts);s.SetWidth(mm(.05));b.Add(s)
    t=k.PCB_TEXT(b);t.SetText('AFO Rev B / '+spec['board'].upper());t.SetPosition(xy(w/2,h-2));t.SetTextSize(xy(.9,.9));t.SetTextThickness(mm(.13));t.SetLayer(k.B_SilkS);t.SetMirrored(True);b.Add(t)
    k.SaveBoard(str(out/(name+'.kicad_pcb')),b)
    nc={'name':'Default','clearance':.15,'track_width':.2,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.2,'diff_pair_via_gap':.25,'pcb_color':'rgba(0, 0, 0, 0)','schematic_color':'rgba(0, 0, 0, 0)'}
    project={'meta':{'filename':name+'.kicad_pro','version':1},'net_settings':{'classes':[nc],'meta':{'version':4}},'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.5,'min_hole_clearance':.15,'min_through_hole_diameter':.2,'min_copper_edge_clearance':.3}}}}
    (out/(name+'.kicad_pro')).write_text(json.dumps(project,indent=2)+'\n')
    (out/'fp-lib-table').write_text('(fp_lib_table (lib (name "RevB") (type "KiCad") (uri "${KIPRJMOD}/../RevB.pretty") (options "") (descr "Revision B project footprints")))\n')
    with (out/'bom.csv').open('w') as f:
        wr=csv.writer(f);wr.writerow(['Reference','Value','Manufacturer part number','Footprint','Populate'])
        for p in spec['parts']:wr.writerow([p['ref'],p['value'],p['mpn'],p['footprint'],'Yes' if p['pins'] else 'Mechanical'])
    print(name,len(spec['parts']),'footprints /',len(nets),'nets')
    # Export from a reloaded board so project netclasses are honored.
    b=k.LoadBoard(str(out/(name+'.kicad_pcb')))
    k.ExportSpecctraDSN(b,str(out/(name+'.dsn')))
    dsn=out/(name+'.dsn');dsn.write_text(dsn.read_text().replace('(layer In1.Cu\n      (type signal)', '(layer In1.Cu\n      (type power)'))
if __name__=='__main__':
    custom()
    import sys
    for name in sys.argv[1:] or ['main']:board(json.loads((ROOT/'design'/(name+'.json')).read_text()))
