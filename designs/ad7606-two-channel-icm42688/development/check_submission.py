#!/usr/bin/env python3
"""Check evidence completeness only. Never certify electrical or human-use safety."""
import argparse,csv,hashlib,json,re
from pathlib import Path

def review(folder):
    folder=Path(folder).resolve(); missing=[]; hashes={}
    try: data=json.loads((folder/'submission.json').read_text())
    except (OSError,ValueError) as e:return {'status':'INCOMPLETE','engineering_approval':False,'issues':[str(e)],'sha256':{}}
    if not isinstance(data,dict):return {'status':'INCOMPLETE','engineering_approval':False,'issues':['submission.json must contain an object'],'sha256':{}}
    for key in ('build','hardware_revision','operator','date','changes_since_last_stage','instrument_list','evidence_files'):
        if not data.get(key):missing.append('Missing '+key)
    stage=data.get('stage')
    if type(stage) is not int or not 0<=stage<=10:missing.append('stage must be integer 0-10')
    if data.get('build')!='ad7606-two-channel-icm42688':missing.append('Wrong build')
    if type(stage) is int and stage>=2 and not re.fullmatch('[0-9a-fA-F]{64}',str(data.get('firmware_sha256',''))):missing.append('Need actual firmware application SHA-256')
    files=data.get('evidence_files',[])
    if not isinstance(files,list):missing.append('evidence_files must be a list');files=[]
    for item in files:
        if not isinstance(item,str):missing.append('Invalid evidence filename');continue
        p=(folder/item).resolve()
        if not p.is_relative_to(folder):missing.append('Evidence outside submission: '+item);continue
        if not p.is_file() or p.stat().st_size==0:missing.append('Missing/empty evidence: '+item);continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        hashes[item]=h.hexdigest()
    if type(stage) is int and stage>0:
        try:
            with (folder/'measurements.csv').open() as source:
                rows=list(csv.DictReader(source))
            if not rows:missing.append('No measurement rows')
            # Use the packaged plan, not the submitted worksheet, as the checklist.
            plan=json.loads(Path(__file__).with_name('stage-plan.json').read_text())
            expected={check['id'] for item in plan['stages'] if item['stage']==stage for check in item['checks']}
            observed={str(row.get('check_id') or '') for row in rows}
            for check in sorted(expected-observed):missing.append('Missing required check: '+check)
            for check in sorted(observed-expected):missing.append('Unknown check: '+str(check))
            for row in rows:
                tag=str(row.get('check_id') or 'unknown')
                if row.get('outcome') not in ('PASS','FAIL','PENDING'):missing.append(tag+': outcome not recorded')
                for key in ('measured_value','unit','uncertainty','instrument_settings','evidence_file','operator','date'):
                    if not row.get(key):missing.append(tag+': missing '+key)
                if row.get('evidence_file') not in files:missing.append(tag+': evidence file not listed')
                if row.get('outcome')!='PASS':missing.append(tag+': requires review before advancing')
        except (OSError,ValueError,csv.Error):missing.append('Unreadable measurements or packaged stage plan')
    return {'status':'INCOMPLETE' if missing else 'READY FOR HUMAN REVIEW','engineering_approval':False,'issues':missing,'sha256':hashes,'notice':'Completeness only: values, traces, limits and safety require review. Do not infer permission to advance.'}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('folder');args=a.parse_args()
    result=review(args.folder);print(json.dumps(result,indent=2));return 2 if result['issues'] else 0
if __name__=='__main__':raise SystemExit(main())
