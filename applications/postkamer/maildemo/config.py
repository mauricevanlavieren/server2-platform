"""Explicit local/container configuration; no credentials or external endpoints."""
import os
import re
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    bind: str
    port: int
    db: Path
    allowed_hosts: tuple[str, ...]

def load_config(env=None):
    env=os.environ if env is None else env
    bind=env.get('POSTKAMER_BIND','127.0.0.1')
    if bind not in ('127.0.0.1','0.0.0.0'):raise ValueError('Ongeldige IPv4-binding')
    port=int(env.get('POSTKAMER_PORT','8765'))
    if not 1024<=port<=65535:raise ValueError('Ongeldige poort')
    raw=env.get('POSTKAMER_DB','.local/demo.sqlite')
    if not raw.strip() or '\x00' in raw:raise ValueError('Ongeldig databasepad')
    hosts=tuple(x.strip() for x in env.get('POSTKAMER_ALLOWED_HOSTS',f'127.0.0.1:{port},localhost:{port}').split(','))
    if not hosts or len(hosts)>8 or any(not re.fullmatch(r'(?:localhost|127\.0\.0\.1):[0-9]{4,5}',x) or not 1024<=int(x.rsplit(':',1)[1])<=65535 for x in hosts):raise ValueError('Alleen expliciete loopback-authorities toegestaan')
    return Config(bind,port,Path(raw),hosts)
