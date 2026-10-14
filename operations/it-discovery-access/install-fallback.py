"""Install only Kompas's managed loopback fallback in the current laptop account."""
from pathlib import Path
import os,subprocess
source=Path(__file__).resolve().parent
if Path.home()!=Path('/home/mau'):raise SystemExit('Wrong laptop account')
folder=Path.home()/'.local/lib/kompas-access';unitdir=Path.home()/'.config/systemd/user'
if folder.is_symlink() or unitdir.is_symlink():raise SystemExit('Symlink destination; STOP')
folder.mkdir(parents=True,exist_ok=True);unitdir.mkdir(parents=True,exist_ok=True)
for src,dest,marker,mode in [('fallback.py',folder/'fallback.py','Managed Kompas loopback fallback',0o700),('kompas-fallback.service',unitdir/'kompas-fallback.service','Description=Kompas managed localhost fallback',0o644)]:
 if dest.is_symlink() or (dest.exists() and marker not in dest.read_text()):raise SystemExit('Unmanaged destination; STOP')
 dest.write_text((source/src).read_text());dest.chmod(mode)
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','enable','--now','kompas-fallback.service'],check=True)
print('Installed own loopback-only fallback. Status: systemctl --user status kompas-fallback.service')
