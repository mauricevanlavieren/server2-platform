"""Managed mau2-only backup worker. Root execution; never prints recovery secrets."""
import fcntl,json,os,shutil,sqlite3,subprocess,sys,time,hashlib
from pathlib import Path
ROOT=Path('/var/lib/it-discovery-backup');REPO=Path('/var/backups/restic');PASS=Path('/etc/it-discovery-backup/restic-password');STAGE=ROOT/'staging';STATE=ROOT/'forgejo-recovery.json'
def cmd(args,timeout=180):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError('command failed: '+Path(args[0]).name+' code '+str(r.returncode))
 return r.stdout
K=['/usr/local/bin/k3s','kubectl','--request-timeout=8s','--cache-dir=/var/lib/it-discovery-backup/kube-cache']
def k(*args):return cmd(K+list(args),timeout=120)
def recover():
 if not STATE.exists():return
 s=json.loads(STATE.read_text());assert s['namespace']=='forgejo' and s['name']=='forgejo' and s['replicas']==1
 k('scale','deployment/forgejo','-n','forgejo','--replicas=1')
 k('patch','kustomization','forgejo','-n','flux-system','--type=merge','-p',json.dumps({'spec':{'suspend':s['suspend']}}))
 k('rollout','status','deployment/forgejo','-n','forgejo','--timeout=90s');STATE.unlink()
def preserve_owners(source,target):
 for src in [Path(source),*Path(source).rglob('*')]:
  dst=Path(target)/src.relative_to(source);st=src.lstat()
  if dst.exists() or dst.is_symlink():os.chown(dst,st.st_uid,st.st_gid,follow_symlinks=False)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.digest()
def sqlite_snapshot(source,target):
 deadline=time.monotonic()+120
 def progress(*_):
  if time.monotonic()>deadline:raise TimeoutError('SQLite snapshot deadline')
 target.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=10) as src,sqlite3.connect(target) as dst:
  src.backup(dst,pages=256,progress=progress,sleep=.05);assert dst.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 st=source.stat();os.chown(target,st.st_uid,st.st_gid);target.chmod(st.st_mode & 0o777)
def main():
 if os.geteuid()!=0 or os.uname().nodename!='mau2':raise RuntimeError('Only root on mau2')
 os.umask(0o077);ROOT.mkdir(mode=0o700,exist_ok=True)
 if '--recover' in sys.argv:recover();return
 lock=(ROOT/'backup.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 assert PASS.is_file() and REPO.is_dir()
 if shutil.disk_usage('/').free<15*1024**3:raise RuntimeError('Less than 15GiB disk free')
 if STAGE.exists():shutil.rmtree(STAGE) # only our own managed staging
 STAGE.mkdir(mode=0o700)
 if (Path('/var/lib/rancher/k3s/server/db/etcd')).exists():raise RuntimeError('Expected SQLite; not etcd')
 db=Path('/var/lib/rancher/k3s/server/db/state.db');assert db.is_file()
 shutil.copytree('/var/lib/rancher/k3s/server',STAGE/'k3s/server',ignore=shutil.ignore_patterns('db','logs'),symlinks=True)
 sqlite_snapshot(db,STAGE/'k3s/server/db/state.db')
 shutil.copytree('/etc/rancher/k3s',STAGE/'k3s/etc',symlinks=True)
 # Existing application pause is allowed ONLY after explicit owner approval.
 if '--maintenance-approved' not in sys.argv:raise RuntimeError('Forgejo maintenance approval required')
 f=json.loads(k('get','deployment','forgejo','-n','forgejo','-o','json'));assert f['spec']['replicas']==1
 flux=json.loads(k('get','kustomization','forgejo','-n','flux-system','-o','json'))
 STATE.write_text(json.dumps({'namespace':'forgejo','name':'forgejo','replicas':1,'suspend':flux['spec'].get('suspend',False)}));STATE.chmod(0o600)
 try:
  k('patch','kustomization','forgejo','-n','flux-system','--type=merge','-p','{"spec":{"suspend":true}}')
  k('scale','deployment/forgejo','-n','forgejo','--replicas=0')
  labels=','.join(a+'='+b for a,b in f['spec']['selector']['matchLabels'].items())
  k('wait','--for=delete','pod','-n','forgejo','-l',labels,'--timeout=90s')
  name=json.loads(k('get','pvc','forgejo-data','-n','forgejo','-o','json'))['spec']['volumeName'];pv=json.loads(k('get','pv',name,'-o','json'));path=Path(pv['spec']['local']['path']).resolve();assert path.is_relative_to('/var/lib/rancher/k3s/storage')
  shutil.copytree(path,STAGE/'forgejo/data',symlinks=True);preserve_owners(path,STAGE/'forgejo/data')
 finally:recover()
 # Other PVCs are captured read-only; SQLite via its Online Backup API, no Postkamer reconfiguration.
 pvlist=json.loads(k('get','pv','-o','json'))['items']
 extra=[]
 for pv in pvlist:
  claim=pv['spec'].get('claimRef',{});namespace=claim.get('namespace','')
  if namespace in ('forgejo','postkamer') or 'local' not in pv['spec']:continue
  if namespace=='it-discovery':
   src=Path(pv['spec']['local']['path']).resolve()/'inventory.sqlite';assert src.is_relative_to('/var/lib/rancher/k3s/storage');sqlite_snapshot(src,STAGE/'it-discovery/inventory.sqlite');continue
  extra.append({'namespace':namespace,'pvc':claim.get('name'),'status':'NOT_INCLUDED_REQUIRES_APP_SPECIFIC_CONSISTENCY'})
 # Postkamer synthetic SQLite data protection without stopping/modifying the app.
 for pv in pvlist:
  if pv['spec'].get('claimRef',{}).get('namespace')=='postkamer':
   src=Path(pv['spec']['local']['path']).resolve()/'demo.sqlite';assert src.is_relative_to('/var/lib/rancher/k3s/storage');sqlite_snapshot(src,STAGE/'postkamer/demo.sqlite')
 (STAGE/'coverage.json').write_text(json.dumps({'other_pvcs':extra,'same_disk_warning':True}))
 restore=ROOT/'restore-test';
 if restore.exists():shutil.rmtree(restore)
 R=['/usr/bin/restic','--repo',str(REPO),'--password-file',str(PASS)]
 cmd(R+['backup','--tag','mau2-platform','--host','mau2',str(STAGE)],timeout=900)
 cmd(R+['check'],timeout=600)
 cmd(R+['restore','latest','--tag','mau2-platform','--target',str(restore)],timeout=600)
 restored=restore/str(STAGE).lstrip('/')
 verified=0
 for original in STAGE.rglob('*'):
  if not original.is_file() or original.is_symlink():continue
  restoredfile=restored/original.relative_to(STAGE);assert digest(original)==digest(restoredfile);assert original.stat().st_uid==restoredfile.stat().st_uid and original.stat().st_gid==restoredfile.stat().st_gid;verified+=1
  if original.name.endswith(('.db','.sqlite')):
   with original.open('rb') as f:signature=f.read(16)
   if signature==b'SQLite format 3\x00':
    with sqlite3.connect(restoredfile.as_uri()+'?mode=ro',uri=True) as db:assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 for git in (restored/'forgejo/data').rglob('HEAD'):
  if git.parent.name.endswith('.git'):cmd(['/usr/bin/git','-c','safe.directory='+str(git.parent),'--git-dir='+str(git.parent),'fsck','--full'],timeout=60)
 cmd(R+['forget','--tag','mau2-platform','--group-by','host,tags','--keep-daily','7','--keep-weekly','4','--keep-monthly','3','--prune'],timeout=900)
 result={'status':'PASS','time':time.time(),'files_restored_verified':verified,'sqlite_integrity':'PASS','git_fsck':'PASS','scope':'encrypted backup plus isolated filesystem restore; no production restore','same_disk_only':True,'uncovered_pvcs':extra}
 (ROOT/'last-result.json').write_text(json.dumps(result));public=Path('/var/lib/it-discovery-agent/public/backup.json');
 if public.parent.is_dir():public.write_text(json.dumps(result));public.chmod(0o644)
 print(json.dumps(result));shutil.rmtree(restore);shutil.rmtree(STAGE)
if __name__=='__main__':
 try:main()
 except Exception as e:
  result={'status':'FAIL','time':time.time(),'error_type':type(e).__name__}
  if ROOT.exists():(ROOT/'last-result.json').write_text(json.dumps(result))
  public=Path('/var/lib/it-discovery-agent/public/backup.json')
  if public.parent.is_dir():public.write_text(json.dumps(result));public.chmod(0o644)
  print('Backup FAIL: '+type(e).__name__+'; no secret data printed',file=sys.stderr);sys.exit(1)
