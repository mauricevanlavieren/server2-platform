"""Portable, consent-bound Linux discovery CLI. No escalation or broad scans."""
import argparse,json,subprocess,sys,csv,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--target',choices=['server2','local'],required=True);p.add_argument('--consent',action='store_true');p.add_argument('--output',type=Path,required=True);p.add_argument('--csv',type=Path);p.add_argument('--import-local',action='store_true');args=p.parse_args()
if not args.consent:p.error('Explicit --consent is required')
probe=Path(__file__).with_name('linux_probe.py').read_text()
command=['ssh','-o','BatchMode=yes','-o','HostName=192.168.0.162','-o','StrictHostKeyChecking=yes','server2','python3 -I -B -'] if args.target=='server2' else [sys.executable,'-I','-B','-']
r=subprocess.run(command,input=probe,text=True,capture_output=True,timeout=20)
if r.returncode:raise SystemExit('Discovery failed; raw stderr withheld')
d=json.loads(r.stdout)
if d.get('schema')!='kompas.discovery.v1' or d.get('read_only') is not True or not isinstance(d.get('assets'),list):raise SystemExit('Invalid discovery result')
if args.target=='server2' and d.get('source_host')!='mau2':raise SystemExit('Wrong server identity')
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('x') as f:json.dump(d,f,indent=2)
args.output.chmod(0o600)
if args.csv:
 with args.csv.open('x',newline='') as f:
  w=csv.writer(f);w.writerow(['name','kind','observed','source']);w.writerows([[a['name'],a['kind'],d['observed'],'Linux probe'] for a in d['assets']])
 args.csv.chmod(0o600)
if args.import_local:
 if d['source_host']!='mau2':raise SystemExit('Only mau2 imports authorized; file retained locally')
 d['consent']=True;url='http://127.0.0.1:8780';req=urllib.request.Request(url+'/api/toolkit',data=json.dumps(d).encode(),headers={'Content-Type':'application/json','Origin':url})
 with urllib.request.urlopen(req,timeout=10) as response:print('Import status',response.status)
print('PASS: scoped Linux discovery exported; no network scan or privilege escalation')
