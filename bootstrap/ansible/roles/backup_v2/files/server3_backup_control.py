#!/usr/bin/env python3
"""Restricted persistent SSH guard. Power operations are deliberately absent."""
import fcntl
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import subprocess
import sys
import time

UUID = '67837227-f008-4257-822a-b4562efa2daa'
OPS = {'check', 'lease-acquire', 'lease-renew', 'lease-release'}
class Rejected(RuntimeError):
    pass

def require(ok, message):
    if not ok:
        raise Rejected(message)

def request(raw):
    require(len(raw) <= 4096, 'oversized request')
    try:
        d = json.loads(raw)
    except ValueError:
        raise Rejected('invalid JSON') from None
    require(isinstance(d, dict) and set(d) == {'op', 'run', 'boot_id'}, 'invalid fields')
    require(isinstance(d['op'], str) and d['op'] in OPS and isinstance(d['run'], str) and re.fullmatch('[a-f0-9]{32}', d['run']), 'invalid operation/run')
    require(d['boot_id'] is None or isinstance(d['boot_id'], str) and
            re.fullmatch('[a-f0-9-]{36}', d['boot_id']), 'invalid boot identity')
    return d

def health(c):
    require(socket.gethostname().split('.')[0] == 'mau3', 'wrong host')
    out = subprocess.run(['findmnt', '--json', '--mountpoint', '/backup', '-o', 'TARGET,SOURCE,FSTYPE,UUID'],
                         capture_output=True, timeout=5)
    require(out.returncode == 0, 'missing mount')
    d = json.loads(out.stdout)['filesystems'][0]
    require(d['target'] == '/backup' and d['source'] == '/dev/md0' and d['fstype'] == 'ext4' and d['uuid'] == UUID, 'mount mismatch')
    root = Path('/sys/block/md0/md')
    require((root / 'degraded').read_text().strip() == '0' and
            (root / 'raid_disks').read_text().strip() == '2', 'unhealthy RAID')
    state = (root / 'array_state').read_text().strip()
    require(state in {'clean', 'active', 'active-idle'}, 'RAID not ready')
    require(not Path('/backup/restic').is_symlink() and
            os.stat('/backup/restic').st_dev == os.stat('/backup').st_dev, 'repository off target')
    v = os.statvfs('/backup')
    require(v.f_bavail * v.f_frsize >= c['min_free_bytes'] and v.f_favail >= 1024, 'insufficient destination capacity')
    require(not Path('/run/server3-backup-control/inhibit').exists(), 'maintenance inhibit')
    return {'host': 'mau3', 'uuid': UUID,
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'lock_count': len(list(Path('/backup/restic/locks').iterdir()))}

class Session:
    def __init__(self, c, probe=health, clock=time.monotonic):
        self.c, self.probe, self.clock = c, probe, clock
        self.owner = None
        self.boot = None
        self.deadline = 0
    def handle(self, d):
        state = self.probe(self.c)
        require(d['boot_id'] is None or d['boot_id'] == state['boot_id'], 'boot changed')
        if self.boot is not None:
            require(self.boot == state['boot_id'], 'boot changed')
        if d['op'] == 'lease-acquire':
            require(self.owner is None and state['lock_count'] == 0, 'lease/repository busy')
            self.owner, self.boot = d['run'], state['boot_id']
            self.deadline = self.clock() + self.c['lease_seconds']
        elif d['op'] in {'lease-renew', 'lease-release'}:
            require(self.owner == d['run'] and self.clock() < self.deadline, 'lease expired/wrong owner')
            if d['op'] == 'lease-release':
                self.owner = None
            else:
                self.deadline = self.clock() + self.c['lease_seconds']
        elif self.owner is not None:
            require(self.owner == d['run'] and self.clock() < self.deadline, 'lease expired/wrong owner')
        return {**state, 'ok': True, 'run': d['run']}

def main():
    try:
        require(len(sys.argv) == 1 and os.geteuid() == 0 and os.environ.get('SUDO_USER') == 'backupctl', 'invalid caller')
        path = Path('/etc/server3-backup-control/config.json')
        s = path.lstat()
        require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o077 and path.resolve() == path, 'unsafe config')
        c = json.loads(path.read_text())
        require(c.get('enabled') is True and c.get('shutdown_enabled') is False and c.get('filesystem_uuid') == UUID,
                'control disabled or unsupported power request')
        require(type(c.get('lease_seconds')) is int and 10 <= c['lease_seconds'] <= 60, 'invalid lease lifetime')
        require(type(c.get('min_free_bytes')) is int and c['min_free_bytes'] >= 268435456, 'invalid capacity minimum')
        health(c)
        state = Path('/run/server3-backup-control')
        state.mkdir(mode=0o700, exist_ok=True)
        require(state.resolve() == state and state.stat().st_uid == 0 and stat.S_IMODE(state.stat().st_mode) == 0o700, 'unsafe state path')
        fd = os.open(state / 'session.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # This cwd pins the actual mount until the SSH session exits.
            os.chdir('/backup')
            held_dev = os.stat('.').st_dev
            session = Session(c)
            raw = bytearray()
            idle_deadline = time.monotonic() + c['lease_seconds']
            while True:
                require(time.monotonic() < idle_deadline, 'idle control session expired')
                if session.owner is not None:
                    require(time.monotonic() < session.deadline, 'lease expired')
                ready, _, _ = select.select([sys.stdin], [], [], 1)
                if not ready:
                    continue
                char = os.read(sys.stdin.fileno(), 1)
                if not char:
                    break
                raw.extend(char)
                require(len(raw) <= 4096, 'oversized request')
                if char != b'\n':
                    continue
                require(os.stat('/backup').st_dev == held_dev, 'mount replaced')
                d = request(raw)
                raw.clear()
                reply = session.handle(d)
                idle_deadline = time.monotonic() + c['lease_seconds']
                print(json.dumps(reply), flush=True)
                if d['op'] == 'lease-release':
                    break
        return 0
    except (Rejected, OSError, ValueError, KeyError, subprocess.SubprocessError):
        print(json.dumps({'ok': False, 'detail': 'control refused; no power action executed'}), flush=True)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
