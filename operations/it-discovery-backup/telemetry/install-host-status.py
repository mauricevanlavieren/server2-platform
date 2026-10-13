"""Laptop owner installer; fixed mau2 SSH target and hidden interactive sudo."""
import json,base64,subprocess,shlex
from pathlib import Path
worker=Path(__file__).with_name('host-status.py').read_text()
code=r'''import os,sys,json,base64,subprocess
from pathlib import Path
if os.geteuid()!=0 or os.uname().nodename!='mau2':raise SystemExit('Wrong host/privilege')
p=Path('/opt/it-discovery-backup');assert (p/'backup-run.py').exists()
(p/'host-status.py').write_text(base64.b64decode(sys.argv[1]).decode());(p/'host-status.py').chmod(0o600)
unit='''+repr('''[Unit]
Description=Kompas fixed-scope host telemetry
After=k3s.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 -I -B /opt/it-discovery-backup/host-status.py
User=root
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/it-discovery-backup
CPUQuota=10%
MemoryMax=128M
TimeoutStartSec=70
''')+r'''
timer='''+repr('''[Unit]
Description=Kompas host telemetry interval
[Timer]
OnBootSec=30
OnUnitActiveSec=60
[Install]
WantedBy=timers.target
''')+r'''
for suffix,text in [('service',unit),('timer',timer)]:
 f=Path('/etc/systemd/system/kompas-host-status.'+suffix)
 if f.exists() and not f.read_text().startswith('[Unit]\nDescription=Kompas'):raise SystemExit('Unmanaged unit; STOP')
 f.write_text(text);f.chmod(0o644)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start','kompas-host-status.service'],check=True)
subprocess.run(['systemctl','enable','--now','kompas-host-status.timer'],check=True)
print('PASS: fixed-scope Kompas telemetry active; no backup password access granted to webapp')
'''
arg=base64.b64encode(worker.encode()).decode()
raise SystemExit(subprocess.run(['ssh','-t','-o','HostName=192.168.0.162','-o','StrictHostKeyChecking=yes','server2','sudo /usr/bin/python3 -c '+shlex.quote(code)+' '+shlex.quote(arg)]).returncode)
