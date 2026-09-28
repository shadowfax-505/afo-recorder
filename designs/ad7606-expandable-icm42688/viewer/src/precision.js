import * as THREE from 'three';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {loadModels,makeModel} from './models.js';
await loadModels();
const catalog=await fetch('models/catalog.json?v=12', {cache:'no-store'}).then(r=>r.json());
let moduleLocations=new Map(),wireObjects=[],wireSelection="";
const $=id=>document.getElementById(id),data=await fetch('../breadboard/assembly.json?v=12', {cache:'no-store'}).then(r=>r.json());
data.physical_harness=await fetch('../breadboard/physical-harness.json?v=12', {cache:'no-store'}).then(r=>r.json());
const systemWiring=await fetch('../breadboard/system-wiring.json?v=12', {cache:'no-store'}).then(r=>r.json());
$('title').textContent=data.title;
const stages=['Power / midpoint','Controller','ADC / DC tests','First EMG','Remaining EMG inputs','Foot + shank IMUs','microSD','Wi-Fi + SD','Battery','MyoWare integration'];
stages.forEach((s,i)=>$('stage').add(new Option(`${i+1}. ${s}`,i+1)));const startParams=new URLSearchParams(location.search);$('stage').value=String(Math.max(1,Math.min(10,Number(startParams.get('stage'))||1)));$('view').value=startParams.get('view')==='detail'?'detail':'whole';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const savedKey='assembly-v2-'+data.variant;let checked=new Set(JSON.parse(localStorage.getItem(savedKey)||'[]')),current=0,board,steps,group=new THREE.Group(),hitTargets=[];
const scene=new THREE.Scene();scene.background=new THREE.Color('#202729');scene.add(group,new THREE.HemisphereLight(0xffffff,0x637e91,2.5));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-40,100,-30);scene.add(light);
const camera=new THREE.PerspectiveCamera(35,1,.1,5000),renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));$('canvas').appendChild(renderer.domElement);const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,0,0);
const color=n=>n==='GND'?'#7d92aa':/3V|5V|VBAT/.test(n)?'#f26968':/RAW|AIN|RC|BUF|VMID/.test(n)?'#f3bd46':'#5de0ca';
function pos(h,y=2.1){let i='abcdefghij'.indexOf(h[0]);return new THREE.Vector3((i<5?i-5.5:i-3.5)*2.54,y,(Number(h.slice(1))-32)*2.54)}
function mesh(g,c,p,opacity=1){let o=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:c,transparent:opacity<1,opacity}));o.position.copy(p);group.add(o);return o}
function line(points,c,r=.25,opacity=1){let curve=new THREE.CatmullRomCurve3(points,false,'centripetal');return mesh(new THREE.TubeGeometry(curve,24,r,7,false),c,new THREE.Vector3(),opacity)}
function label(s,p,size=2.4,c='#f5fbff'){let cv=document.createElement('canvas');cv.width=512;cv.height=72;let ctx=cv.getContext('2d');ctx.font='bold 36px system-ui';cv.width=Math.ceil(ctx.measureText(s).width)+16;ctx.font='bold 36px system-ui';ctx.fillStyle=c;ctx.fillText(s,8,49);let tex=new THREE.CanvasTexture(cv),o=new THREE.Sprite(new THREE.SpriteMaterial({map:tex,depthTest:false}));o.position.copy(p);o.scale.set(size*cv.width/72,size,1);group.add(o);return o}
function drawBoardGeometry(){let s=steps[current];
mesh(new THREE.BoxGeometry(54.6,8.5,165.1),'#dce3e4',new THREE.Vector3(0,-2.75,0));mesh(new THREE.BoxGeometry(3.5,.12,160),'#9aaab2',new THREE.Vector3(0,1.56,0));
for(let row=1;row<=63;row++){for(let side of ['abcde','fghij']){if($('copper').checked){let a=pos(side[0]+row,1.65),b=pos(side[4]+row,1.65);line([a,b],'#bb925c',.65,.65)}for(let col of side){let h=col+row,o=mesh(new THREE.CylinderGeometry(.49,.49,.18,10),'#354e60',pos(h,1.8));o.userData.hole=h;hitTargets.push(o)}}label(String(row),new THREE.Vector3(-20,2.4,(row-32)*2.54),1.5)}
for(const x of [-24.13,-21.59,21.59,24.13])for(let k=0;k<50;k++){const row=3+Math.floor(k/5)*6+k%5;mesh(new THREE.CylinderGeometry(.49,.49,.18,8),'#657782',new THREE.Vector3(x,1.8,(row-32)*2.54));}
for(let col of 'abcdefghij')label(col,pos(col+'1',3).add(new THREE.Vector3(0,0,-4)),1.5);
for(let i=0;i<steps.length;i++){let st=steps[i],active=i===current,opacity=$('isolate').checked&&!active?.17:1;if(st.kind==='component'){let pp=st.pins.map(p=>pos(p.hole));if(st.ref.startsWith('UB')){let center=pp.reduce((a,b)=>a.add(b),new THREE.Vector3()).multiplyScalar(1/pp.length);center.y=5.5;mesh(new THREE.BoxGeometry(6.1,3.5,9.8),active?'#226e85':'#222b34',center,opacity);for(let j=0;j<pp.length;j++){let a=pp[j],b=a.clone();b.x=center.x+Math.sign(a.x-center.x)*3.05;b.y=5;line([a,a.clone().setY(4),b],'#b8c6cd',.18,opacity);if(active)label(String(st.pins[j].pin),a.clone().add(new THREE.Vector3(a.x<0?-1.5:1.5,6,0)),1.5)}mesh(new THREE.SphereGeometry(.7,12,8),'#fae6a9',center.clone().add(new THREE.Vector3(-1.9,2,-3.5)),opacity);if(active)label('NOTCH → row 9',new THREE.Vector3(12,12,center.z-8),2)}else{let a=pp[0],b=pp[1],center=a.clone().add(b).multiplyScalar(.5);center.y=6;let o=mesh(new THREE.BoxGeometry((st.ref.startsWith('R')||st.ref.endsWith('-r')||st.ref.includes('pullup')||st.ref.startsWith('bat-r')||st.ref.startsWith('usb-'))?5:3,2,Math.min(4.2,a.distanceTo(b)*.65)),st.ref.endsWith('-led')?(st.ref.startsWith('rec')?'#2caf61':st.ref.startsWith('err')?'#dc5345':'#eeb045'):(st.ref.startsWith('R')||st.ref.endsWith('-r')||st.ref.includes('pullup')||st.ref.startsWith('bat-r')||st.ref.startsWith('usb-'))?'#c7a672':'#4697bd',center,opacity);for(let p of pp)line([p,p.clone().setY(5),center.clone()],'#bccbd0',.18,opacity)}
}else if(st.kind==='jumper'&&(active||$('allwires').checked)){let a=pos(st.from),b=pos(st.to),h=5+i*.12;line([a,a.clone().setY(h),b.clone().setY(h),b],color(st.net),active?.38:.22,opacity)}
}
if(s){for(let h of s.holes){let p=pos(h,2.15),o=mesh(new THREE.TorusGeometry(1,.23,8,24),'#fef472',p);o.rotation.x=Math.PI/2;s.holes.length<=2&&label(h,p.clone().add(new THREE.Vector3(6,10,0)),3,'#fff682')}if(s.kind==='external'&&!s.endpoint_defined)label('Endpoint requires module qualification',new THREE.Vector3(8,16,0),2.2,'#ffd280')}
render()}

function draw3d(){
 scene.remove(group);group.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose()}});group=new THREE.Group();scene.add(group);hitTargets=[];
 const whole=$('view').value==='whole';$('viewNotice').textContent=whole?'Physical assembly plan: select a wire for exact hole/header labels. Module drawings may be approximate; perform module qualification before power-up.':'Focused insertion guide: switch to Whole setup to see all boards and modules.';
 if(!whole){drawBoardGeometry();return}
 const root=group,selected=board,selectedSteps=steps,selectedIndex=current,isolated=$('isolate').checked,all=$('allwires').checked;
 $('isolate').checked=false;$('allwires').checked=true;
 const visible=data.boards.filter(b=>b.stage<=+$('stage').value&&b.steps.some(s=>!s.stage||s.stage<=+$('stage').value)),locations=new Map();
 for(let i=0;i<visible.length;i++){
  board=visible[i];steps=board.steps.filter(s=>!s.stage||s.stage<=+$('stage').value);current=-1;group=new THREE.Group();const start=hitTargets.length;drawBoardGeometry();const primary=data.boards.filter(b=>!b.auxiliary),aux=data.boards.filter(b=>b.auxiliary);const bi=(board.auxiliary?aux:primary).indexOf(board);group.position.x=board.auxiliary?(bi-(aux.length-1)/2)*68:(bi-(primary.length-1)/2)*68;group.position.z=board.auxiliary?220:0;
  for(const t of hitTargets.slice(start))t.userData.board=board.id;
  const surface=group.children.find(o=>o.isMesh);if(surface){surface.userData.board=board.id;hitTargets.push(surface)}
  label(board.id+' '+(board.auxiliary?'Auxiliary':board.id==='BB0'?'Midpoint':board.id.replace('BB','EMG')),new THREE.Vector3(0,9,-86),8);
  locations.set(board.id,new THREE.Vector3(group.position.x,0,group.position.z));root.add(group);
 }
 group=root;board=selected;steps=selectedSteps;current=selectedIndex;$('isolate').checked=isolated;$('allwires').checked=all;
 const stage=+$('stage').value,modules=new Map();wireObjects=[];$('wireInfo').textContent='Select a solid wire to display its exact endpoints.';$('wireSelect').replaceChildren(new Option('Choose a wire…','')); 
 function module(id,name,x,z,kind=id){const p=new THREE.Vector3(x,3,z),o=makeModel(kind);o.position.copy(p);group.add(o);o.traverse(t=>{if(t.isMesh){t.userData.module=id;hitTargets.push(t)}});label(name,p.clone().add(new THREE.Vector3(0,16,-37)),6);modules.set(id,p);moduleLocations.set(id,{p,kind,name});$('moduleSelect').add(new Option(name,id));}
 function link(){} // Replaced by individual named connections below.

 moduleLocations=new Map();$('moduleSelect').replaceChildren(new Option('Select a module…',''));
 module('reg5','5 V · Pololu 4082',-90,-145);
 module('reg3','3.3 V · Pololu 4980',-30,-145);
 module('ldo','3.0 V · soldered adapter',30,-145);
 if(stage>=2)module('esp','DevKitC-1 N8R8',105,-105);
 if(stage>=3)module('adc',data.title.startsWith('ADS')?'TI ADS131M04EVM':'RBD-3184',-60,-115,data.title.startsWith('ADS')?'ads-evm':'adc');
 if(stage>=6){module('foot','Foot MIKROE-4237',-245,50,'icm');module('shank','Shank MIKROE-4237',-245,115,'icm');}
 if(stage>=7)module('sd','Adafruit 4682',205,-90);
 if(stage>=9)module('battery','Protected LiPo · 328',-160,-125);
 if(modules.has('esp'))link(modules.get('reg5'),modules.get('esp'),'5V');
 if(modules.has('adc'))link(modules.get(data.title.startsWith('ADS')?'ldo':'reg5'),modules.get('adc'),data.title.startsWith('ADS')?'3V0A':'5V');
 link(modules.get('reg3'),modules.get('ldo'),'3V3D');
 for(const id of ['foot','shank','sd'])if(modules.has(id)){link(modules.get('reg3'),modules.get(id),'3V3D');link(modules.get('esp'),modules.get(id),'DIGITAL');}
 if(modules.has('battery'))for(const id of ['reg5','reg3'])link(modules.get('battery'),modules.get(id),'VBAT');
 if(modules.has('adc'))link(modules.get('reg3'),modules.get('adc'),'3V3D / VIO');
 if(modules.has('adc')&&modules.has('esp'))link(modules.get('esp'),modules.get('adc'),'DIGITAL');
 for(const [id,p] of locations){link(modules.get('ldo'),p.clone().add(new THREE.Vector3(-16,0,-40)),'3V0A');if(id!=='BB0'&&modules.has('adc'))link(p.clone().add(new THREE.Vector3(17,0,-40)),modules.get('adc'),'AIN');}
 if(stage>=10)for(let i=1;i<=data.emg_channel_paths;i++){const p=locations.get('BB'+i);if(!p)continue;module('myo'+i,'Bare MyoWare '+i,p.x,115,'myo');link(modules.get('myo'+i),p.clone().add(new THREE.Vector3(0,0,40)),'RAW');}
 if(stage>=8)label('Wi-Fi → laptop (wireless)',new THREE.Vector3(140,16,85),6);
 function wire(id,net,a,b,from,to){const o=line([a,a.clone().setY(20),b.clone().setY(20),b],color(net),.45);o.userData.wire=id;hitTargets.push(o);wireObjects.push({id,net,a,b,from,to,o});$('wireSelect').add(new Option(from+' → '+to+' · '+net,id));}
 const at=(id,h)=>pos(h,2.1).add(locations.get(id));
 for(const b of visible)for(const st of b.steps.filter(s=>s.kind==='jumper'))wire(st.id,st.net,at(b.id,st.from),at(b.id,st.to),b.id+':'+st.from,b.id+':'+st.to);
 for(const w of data.physical_harness||[])if(locations.has(w.a.board)&&locations.has(w.b.board))wire(w.id,w.net,at(w.a.board,w.a.hole),at(w.b.board,w.b.hole),w.a.board+':'+w.a.hole,w.b.board+':'+w.b.hole);

 for(const f of systemWiring.fixtures.filter(f=>f.stage<=stage)){
  const fixturePositions={'power-switch':[-200,-170],'lab-supply':[-260,-170],'button':[215,10],'usb':[145,-165],'usb-dm-r':[126,-146],'usb-dp-r':[140,-137],'usb-q':[75,-145],'cap-2':[26,-148],'cap-3':[34,-148]};const fp=fixturePositions[f.id]||(f.id.startsWith('clamp')?[(Number(f.id.replace('clamp',''))-1-(data.emg_channel_paths-1)/2)*68,90]:[f.x,f.z]);const p=new THREE.Vector3(fp[0],3,fp[1]);modules.set(f.id,p);moduleLocations.set(f.id,{p,kind:(f.id.startsWith('clamp')||f.id==='usb-q')?'adapter':'fixture',name:f.label});
  if(f.id==='usb'){const usbModel=makeModel('usb');usbModel.position.copy(p);group.add(usbModel);}else if(f.id.startsWith('clamp')||f.id==='usb-q'){const adapter=makeModel('adapter');adapter.position.copy(p);group.add(adapter);}else if(f.id.startsWith('cap-'))mesh(new THREE.BoxGeometry(2.5,2,2.5),'#b09555',p);else if(f.inline)mesh(new THREE.BoxGeometry(5,2,2),'#c7a672',p);else mesh(new THREE.BoxGeometry(32,2,22),'#354451',p);label(f.label,p.clone().add(new THREE.Vector3(0,10,-16)),4);$('moduleSelect').add(new Option(f.label,f.id));
 }
 const pendingPorts=new Map();
 for(const w of systemWiring.connections.filter(w=>w.stage<=stage && !(stage>=9 && [w.a.module,w.b.module].includes('lab-supply'))))for(const e of [w.a,w.b]){
  if(e.physical||e.photo_pin||e.adapter_pin||!modules.has(e.module))continue;
  if(!pendingPorts.has(e.module))pendingPorts.set(e.module,[]);
  const list=pendingPorts.get(e.module);if(!list.includes(e.terminal))list.push(e.terminal);
 }
 for(const [id,ports] of pendingPorts){const p=modules.get(id);label('UNRESOLVED — do not connect',p.clone().add(new THREE.Vector3(0,7,18)),2.8,'#ffc36a');}
 function terminal(e){
  if(e.hole)return locations.has(e.module)?at(e.module,e.hole):null;
  if(!modules.has(e.module))return null;
  const p=modules.get(e.module).clone();
  if(e.board_pin)return p.add(new THREE.Vector3(e.board_pin.x,e.board_pin.y,e.board_pin.z));
  if(e.adapter_pin)return p.add(new THREE.Vector3(e.adapter_pin.x,1.6,e.adapter_pin.z));
  if(e.photo_pin)return p.add(new THREE.Vector3(e.photo_pin.x,1.6,e.photo_pin.z));
  if(e.header)return p.add(new THREE.Vector3(e.header==='J1'?-11.43:11.43,0,-29.97+(e.pin-1)*2.54));
  if(e.sd_pin)return p.add(new THREE.Vector3(-10.16+(e.sd_pin-1)*2.54,1.6,8.89));
  const ports=pendingPorts.get(e.module),i=ports.indexOf(e.terminal);
  return p.add(new THREE.Vector3((i%5-2)*5,7,24+Math.floor(i/5)*5));
 }
 for(const w of systemWiring.connections.filter(w=>w.stage<=stage && !(stage>=9 && [w.a.module,w.b.module].includes('lab-supply')))){
  const a=terminal(w.a),b=terminal(w.b);if(!a||!b)continue;
  const pending=!(w.a.physical&&w.b.physical);if(pending&&!$('functional').checked)continue;
  const lift=26+(systemWiring.connections.indexOf(w)%7)*2;
  const points=[a,a.clone().setY(lift),b.clone().setY(lift),b];let o;
  if(pending){o=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),new THREE.LineDashedMaterial({color:color(w.net),dashSize:2,gapSize:1,transparent:true,opacity:.55}));o.computeLineDistances();group.add(o);}
  else{o=line(points,color(w.net),.4);}
  for(const e of [a,b])mesh(new THREE.SphereGeometry(.7,8,6),pending?'#ffb74f':'#83e5ac',e);
  o.userData.wire=w.id;hitTargets.push(o);
  const from=w.a.module+' · '+w.a.terminal,to=w.b.module+' · '+w.b.terminal;
  wireObjects.push({id:w.id,net:w.net,a,b,from,to,o,pending,adapterMapped:!!(w.a.adapter_pin||w.b.adapter_pin),photoMapped:!!(w.a.photo_pin||w.b.photo_pin),note:w.note});$('wireSelect').add(new Option(from+' → '+to+' · '+w.net+(pending?(w.a.adapter_pin||w.b.adapter_pin?' [ADAPTER MAP / ASSEMBLY UNTESTED]':w.a.photo_pin||w.b.photo_pin?' [PHOTO MAP / UNTESTED]':' [MAP PENDING]'):''),w.id));
 }
 window.wiringCoverage={visible:wireObjects.length,systemConnections:systemWiring.connections.length,physicalRelease:false};
 if(wireSelection&&wireObjects.some(w=>w.id===wireSelection))inspectWire(wireSelection);


 
 render();
}

function render(){renderer.render(scene,camera)}
function fit(top=false){const box=new THREE.Box3().setFromObject(group),center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3());const halfFov=THREE.MathUtils.degToRad(camera.fov/2),aspect=Math.max(.3,camera.aspect);const distance=top?(Math.max(size.z,size.x/aspect)/2/Math.tan(halfFov)+size.y)*1.12:box.getBoundingSphere(new THREE.Sphere()).radius/Math.sin(Math.min(halfFov,Math.atan(Math.tan(halfFov)*aspect)))*1.05;camera.up.set(0,1,0);camera.position.copy(center).add(top?new THREE.Vector3(0,distance,.01):new THREE.Vector3(.35,1,.8).normalize().multiplyScalar(distance));controls.target.copy(center);controls.update();render()}
function mapSVG(){const s=steps[current],high=new Set(s?.holes||[]),x=h=>60+('abcdefghij'.indexOf(h[0])+('abcdefghij'.indexOf(h[0])>=5?2:0))*38,y=h=>72+(Number(h.slice(1))-1)*27;let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 510 1800"><rect width="510" height="1800" fill="#fff"/><text x="25" y="25" font-family="sans-serif" font-size="17">${board.id} · ${esc(board.role)} · component side</text><rect x="230" y="55" width="76" height="1710" fill="#edf1f4"/>`;
for(let row=1;row<=63;row++){svg+=`<text x="13" y="${y('a'+row)+4}" font-family="sans-serif" font-size="13">${row}</text>`;for(let side of ['abcde','fghij']){svg+=`<path d="M${x(side[0]+row)},${y('a'+row)} H${x(side[4]+row)}" stroke="#d5b581" stroke-width="7"/>`;for(let c of side){let h=c+row,occ=board.holes[h],hi=high.has(h);svg+=`<g data-hole="${h}"><circle cx="${x(h)}" cy="${y(h)}" r="${hi?9:5}" fill="${hi?'#ffe34d':occ?'#257985':'#eff5f8'}" stroke="#506575"/><text x="${x(h)+7}" y="${y(h)+4}" font-family="sans-serif" font-size="9" fill="#314956">${h}</text></g>`}}}
for(let c of 'abcdefghij')svg+=`<text x="${x(c+'1')-4}" y="48" font-family="sans-serif" font-size="16">${c}</text>`;
if(s?.kind==='jumper')svg+=`<path d="M${x(s.from)},${y(s.from)} Q${Math.max(x(s.from),x(s.to))+22},${(y(s.from)+y(s.to))/2} ${x(s.to)},${y(s.to)}" fill="none" stroke="${color(s.net)}" stroke-width="3" pointer-events="none"/>`;
svg+='<text x="20" y="1790" font-family="sans-serif" font-size="12">Each gold horizontal strip connects 5 holes. No connection across the gap.</text></svg>';return svg}
function holeInfo(h){const row=h.slice(1),strip=(h[0]<'f'?'abcde':'fghij').split('').map(c=>c+row);$('holeDetail').textContent=`${board.id}:${h}\nConnected strip: ${strip.join(', ')}\nNet: ${board.nets[h]||'unassigned'}\n`+strip.map(k=>`${k}: ${(board.holes[k]||[]).join('; ')||'empty'}`).join('\n')}
function select(i){current=Math.max(0,Math.min(steps.length-1,i));const s=steps[current];$('position').textContent=`${current+1} / ${steps.length}`;$('stepTitle').textContent=s.title;$('instruction').textContent=s.instruction;$('endpoints').innerHTML=s.holes.map(h=>`<span class="endpoint">${board.id}:${esc(h)}</span>`).join('');$('orientation').textContent=s.orientation||'';$('gate').className=s.kind==='external'?'blocked':'';$('gate').textContent=s.kind==='external'?`CONNECTION: ${s.to}. Follow the module qualification guide, then check unpowered continuity.`:'After insertion, inspect both ends and check unpowered continuity against the strip map.';$('done').checked=checked.has(s.id);$('done').disabled=s.kind==='external'&&!s.endpoint_defined;$('prev').disabled=current===0;$('next').disabled=current===steps.length-1;
$('steps').innerHTML=steps.map((st,j)=>`<button data-step="${j}" class="${j===current?'selected ':''}${st.kind==='external'?'external ':''}${checked.has(st.id)?'checked':''}">${j+1}. ${esc(st.title)}</button>`).join('');$('steps').querySelectorAll('button').forEach(b=>b.onclick=()=>select(+b.dataset.step));$('map').innerHTML=mapSVG();$('map').querySelectorAll('[data-hole]').forEach(e=>e.onclick=()=>holeInfo(e.dataset.hole));draw3d();$('printTable').innerHTML=`<h2>${esc(data.title)} / ${board.id}</h2><p>Use the module qualification guide before connecting power. Printed terminal identities define wiring; rendered dimensions are not a mounting template.</p><table><thead><tr><th>Step</th><th>Part / net</th><th>Insertion holes / endpoint</th><th>Instruction</th></tr></thead><tbody>${steps.map((st,j)=>`<tr><td>${j+1}</td><td>${esc(st.title)}</td><td>${esc(st.holes.join(', '))}${st.kind==='external'?' → '+esc(st.to):''}</td><td>${esc(st.instruction)} ${esc(st.orientation||'')}</td></tr>`).join('')}</tbody></table>`}
function loadBoard(){board=data.boards.find(b=>b.id===$('board').value);steps=board.steps.filter(s=>!s.stage||s.stage<=+$('stage').value);$('counts').textContent=`${data.emg_channel_paths} physical EMG input paths · ${board.steps.filter(s=>s.kind==='external').length} external leads on this board`;select(0);fit(true)}
function stageChange(){const stage=+$('stage').value,old=$('board').value;$('board').replaceChildren();for(let b of data.boards.filter(b=>b.stage<=stage&&b.steps.some(s=>!s.stage||s.stage<=stage)))$('board').add(new Option(b.id+' · '+b.role,b.id));if([...$('board').options].some(o=>o.value===old))$('board').value=old;else $('board').value=$('board').options[0].value;$('stageScope').textContent=data.stage_scope[stage-1];loadBoard()}
$('stage').onchange=stageChange;$('board').onchange=()=>{$('view').value='detail';loadBoard()};$('view').onchange=()=>{draw3d();fit(true)};$('next').onclick=()=>select(current+1);$('prev').onclick=()=>select(current-1);$('top').onclick=()=>fit(true);$('angle').onclick=()=>fit(false);$('fit').onclick=()=>fit(true);$('focus').onclick=()=>{$('view').value='detail';draw3d();const pp=steps[current].holes.map(h=>pos(h));const center=pp.reduce((a,b)=>a.add(b),new THREE.Vector3()).multiplyScalar(1/pp.length);const span=Math.max(18,...pp.map(p=>p.distanceTo(center)*2));controls.target.copy(center);camera.position.copy(center.clone().add(new THREE.Vector3(0,span*2.5,.01)));controls.update();render()};$('print').onclick=()=>window.print();for(let id of ['isolate','copper','allwires'])$(id).onchange=draw3d;$('done').onchange=()=>{const id=steps[current].id;$('done').checked?checked.add(id):checked.delete(id);localStorage.setItem(savedKey,JSON.stringify([...checked]));select(current)};
function canvasHit(e){const r=renderer.domElement.getBoundingClientRect(),ray=new THREE.Raycaster();ray.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),camera);return ray.intersectObjects(hitTargets)[0]}
renderer.domElement.onclick=e=>{const hit=canvasHit(e);if(!hit)return;const d=hit.object.userData;if(d.wire)inspectWire(d.wire);if(d.module)inspectModule(d.module);if(d.hole)holeInfo(d.hole)};
renderer.domElement.ondblclick=e=>{if($('view').value!=='whole')return;const hit=canvasHit(e);if(!hit?.object.userData.board)return;$('board').value=hit.object.userData.board;$('view').value='detail';loadBoard()};
function resize(){let r=$('canvas').getBoundingClientRect();renderer.setSize(r.width,r.height);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();render()}window.onresize=resize;controls.addEventListener('change',render);resize();stageChange();window.assemblyWorkbench={get board(){return board.id},get step(){return steps[current]},get boardCount(){return data.boards.length},get view(){return $('view').value}};

function inspectModule(id){const m=moduleLocations.get(id);if(!m)return;$('moduleSelect').value=id;const c=m.kind==='fixture'?{status:'Off-board wired component; see physical assembly instructions',dimensions:'Illustrative component body; use terminal labels',notes:'One wire per connector. Selected source is lab supply at stages 1–8, battery at 9–10.',source:''}:(catalog[m.kind]||catalog.pending);$('moduleInfo').textContent=m.name+'\n'+c.status+'\n'+c.dimensions+'\n'+c.notes;$('moduleSource').href=c.source||'../docs/selected-lab-parts.md';$('moduleSource').textContent=c.source?'Manufacturer reference':'Selection requirements';}
$('moduleSelect').onchange=()=>inspectModule($('moduleSelect').value);
$('moduleZoom').onclick=()=>{const m=moduleLocations.get($('moduleSelect').value);if(!m)return;controls.target.copy(m.p);camera.position.copy(m.p.clone().add(new THREE.Vector3(45,115,80)));controls.update();render()};

function inspectWire(id){const w=wireObjects.find(w=>w.id===id);if(!w)return;wireSelection=id;$('wireSelect').value=id;$('wireInfo').textContent=w.net+'\nFROM '+w.from+'\nTO '+w.to+(w.pending?(w.adapterMapped?'\nADAPTER HEADER CAD-MAPPED. Remote endpoint may remain unmapped. Verify soldered adapter orientation; see adapter-assembly.md.':w.photoMapped?'\nPHOTO-LABELED HEADER endpoint. Electrical continuity untested; board dimensions and rendered locations remain approximate.':'\nNAMED TERMINALS ONLY. Amber dots are virtual terminals, not physical header pins.'):'\nTerminal identity specified. Wire bend and module position are illustrative. Module qualification and unpowered continuity required.')+'\n'+(w.note||'');for(const q of wireObjects){q.o.material.color.set(q.id===id?'#ffff66':color(q.net));q.o.material.transparent=true;q.o.material.opacity=q.id===id?1:.12;}group.children.filter(o=>o.userData.wireLabel).forEach(o=>{group.remove(o);o.material.map?.dispose();o.material.dispose()});for(const [p,t] of [[w.a,w.from],[w.b,w.to]]){const l=label(t,p.clone().add(new THREE.Vector3(0,12,0)),5,'#ffff66');l.userData.wireLabel=true;}render();}
$('wireSelect').onchange=()=>inspectWire($('wireSelect').value);
$('wireZoom').onclick=()=>{const w=wireObjects.find(w=>w.id===wireSelection);if(!w)return;const c=w.a.clone().add(w.b).multiplyScalar(.5),d=Math.max(65,w.a.distanceTo(w.b)*1.8);controls.target.copy(c);camera.position.copy(c.clone().add(new THREE.Vector3(0,d,.01)));controls.update();render()};
$('functional').onchange=draw3d;
