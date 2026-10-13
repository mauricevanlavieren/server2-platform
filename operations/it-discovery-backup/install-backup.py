"""Laptop installer: sudo password only in owner's SSH terminal, no secrets in payload."""
from pathlib import Path
import base64,json,subprocess,shlex,sys
if '--maintenance-approved' not in sys.argv:raise SystemExit('STOP: obtain explicit consent for short Forgejo backup maintenance, then use --maintenance-approved')
worker=Path(__file__).with_name('backup-run.py').read_text()
service='''[Unit]
Description=Mau2 encrypted backup and isolated restore verification
After=k3s.service network-online.target
[Service]
Type=oneshot
User=root
UMask=0077
ExecStart=/usr/bin/python3 /opt/it-discovery-backup/backup-run.py --maintenance-approved
ExecStopPost=/usr/bin/python3 /opt/it-discovery-backup/backup-run.py --recover
Nice=19
CPUQuota=100%
MemoryMax=768M
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
TimeoutStartSec=30min
TimeoutStopSec=120
'''
timer='''[Unit]
Description=Daily mau2 encrypted backup
[Timer]
OnCalendar=*-*-* 03:30:00 UTC
Persistent=true
RandomizedDelaySec=300
[Install]
WantedBy=timers.target
'''
bundle=base64.b64encode(json.dumps({'worker':worker,'service':service,'timer':timer}).encode()).decode()
remote=r'''import base64,json,sys,os,subprocess,secrets
from pathlib import Path
if os.geteuid()!=0 or os.uname().nodename!='mau2':raise SystemExit('Wrong host or privilege')
os.umask(0o077)
b=json.loads(base64.b64decode(sys.argv[1]))
marker=Path('/etc/it-discovery-backup/managed')
for p in ['/opt/it-discovery-backup','/etc/it-discovery-backup','/var/backups/restic','/var/lib/it-discovery-backup']:
 if Path(p).exists() and not marker.exists():raise SystemExit('Existing unmanaged backup path; STOP')
if not Path('/var/lib/rancher/k3s/server/db/state.db').is_file():raise SystemExit('Expected SQLite not found; STOP')
if not Path('/usr/bin/restic').exists():
 subprocess.run(['/usr/bin/apt-get','update'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'NEEDRESTART_MODE':'l','DEBIAN_FRONTEND':'noninteractive'})
 subprocess.run(['/usr/bin/apt-get','install','-y','--no-install-recommends','restic'],check=True,stdout=subprocess.DEVNULL,env={**os.environ,'NEEDRESTART_MODE':'l','DEBIAN_FRONTEND':'noninteractive'})
for p in ['/opt/it-discovery-backup','/etc/it-discovery-backup','/var/backups/restic','/var/lib/it-discovery-backup']:
 Path(p).mkdir(parents=True,exist_ok=True);Path(p).chmod(0o700)
marker.write_text('mau2 it discovery managed backup\n')
password=Path('/etc/it-discovery-backup/restic-password')
if not password.exists():password.write_text(secrets.token_urlsafe(48)+'\n')
password.chmod(0o600)
if not Path('/var/backups/restic/config').exists():
 subprocess.run(['/usr/bin/restic','--repo','/var/backups/restic','--password-file',str(password),'init'],check=True,stdout=subprocess.DEVNULL)
Path('/opt/it-discovery-backup/backup-run.py').write_text(b['worker'])
for name in ['service','timer']:
 f=Path('/etc/systemd/system/it-discovery-backup.'+name)
 if f.exists() and not f.read_text().startswith('[Unit]\nDescription=Mau2') and name=='service':raise SystemExit('Unmanaged service; STOP')
 f.write_text(b[name]);f.chmod(0o644)
subprocess.run(['/usr/bin/systemctl','daemon-reload'],check=True)
# Validate initial backup/restore BEFORE enabling the daily timer.
subprocess.run(['/usr/bin/systemctl','start','it-discovery-backup.service'],check=True)
r=json.loads(Path('/var/lib/it-discovery-backup/last-result.json').read_text())
if r['status']!='PASS':raise SystemExit('Backup gate FAIL; timer not enabled')
subprocess.run(['/usr/bin/systemctl','enable','--now','it-discovery-backup.timer'],check=True)
public=Path('/var/lib/it-discovery-agent/public');public.mkdir(parents=True,exist_ok=True);public.chmod(0o755)
f=public/'backup.json';f.write_text(json.dumps(r));f.chmod(0o644)
print(json.dumps(r))
print('PASS: daily encrypted backup enabled; local same-disk repository does NOT protect against disk/host loss. Password stays root-only; arrange owner offline escrow.')
'''
command='sudo /usr/bin/python3 -c '+shlex.quote(remote)+' '+shlex.quote(bundle)
r=subprocess.run(['ssh','-t','-o','HostName=192.168.0.162','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','server2',command])
sys.exit(r.returncode)
