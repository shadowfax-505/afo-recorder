#!/usr/bin/env python3
import csv,json,hashlib,subprocess
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
P=Path(__file__).resolve().parents[1];D=P/'development'
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
read=lambda p:list(csv.DictReader(p.open()))
master=read(P/'breadboard/system-wiring.csv');collected=[];results=[];links=0
for stage in range(11):
 f=D/f'{stage:02d}';w=read(f/'new-wires.csv');assert all(int(x['Stage'])==stage for x in w);collected+=w
 r=read(f/'measurements.csv');assert all(x['outcome']=='NOT TESTED' and not x['measured_value'] for x in r);results+=r
 data=json.loads((f/'submission.json').read_text());assert data['stage']==stage and data['review_status']=='NOT REVIEWED'
assert sorted(collected,key=lambda x:x['Wire'])==sorted(master,key=lambda x:x['Wire'])
assert len(results)==30
for page in list(D.glob('**/*.html'))+[P/'docs/understanding-the-recorder.html']:
 parser=Links();parser.feed(page.read_text())
 for link in parser.links:
  url=urlsplit(link)
  if url.scheme or url.netloc or not url.path:continue
  assert (page.parent/unquote(url.path)).exists(),(page,link)
  links+=1
# Verify tracked source files of all five other designs against pre-work HEAD.
repo=P.parents[1];protected=[]
for relative in subprocess.check_output(['git','ls-files','designs'],cwd=repo,text=True).splitlines():
 if relative.startswith('designs/'+P.name+'/'):continue
 path=repo/relative
 if path.is_file():
  expected=subprocess.check_output(['git','rev-parse','HEAD:'+relative],cwd=repo,text=True).strip()
  observed=subprocess.check_output(['git','hash-object',relative],cwd=repo,text=True).strip()
  assert observed==expected,relative
  protected.append(relative)
report={'status':'PASS','date':'2026-10-04','stage_folders':11,'wire_rows_partitioned_exactly':len(collected),'blank_measurement_checks':len(results),'local_links':links,'other_design_files_unchanged':len(protected),'physical_measurements_completed':0,'scope':'Stage organization, links, blank forms, unchanged variants; not hardware performance'}
(D/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
