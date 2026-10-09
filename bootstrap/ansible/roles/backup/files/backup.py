#!/usr/bin/env python3
"""Preparation only: explicit enablement + external initialized repository required.
No init, restore, prune, shell hooks, local backend, or Kubernetes mutations.
"""
import argparse
from contextlib import closing
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

CONFIG = Path('/etc/server2-backup/config.json')
STATE = Path('/var/lib/server2-backup')
STAGE = Path('/run/server2-backup')
DB = Path('/var/lib/rancher/k3s/server/db/state.db')
TOKEN = Path('/var/lib/rancher/k3s/server/token')
TLS = Path('/var/lib/rancher/k3s/server/tls')


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def private_file(path):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o077,
            'credential/config must be a private root-owned regular file')
    require(s.st_size > 0, 'empty credential/config')


def configuration(path=CONFIG):
    private_file(path)
    c = json.loads(path.read_text())
    require(c.get('enabled') is True, 'DISABLED: backups not authorized/enabled')
    uri = c.get('repository', '')
    require(uri.startswith('rest:https://'), 'BLOCKED: external TLS REST backend required')
    u = urlsplit(uri[5:])
    host = (u.hostname or '').lower()
    require(host and host == c.get('destination_host', '').lower(), 'destination host missing/mismatch')
    require(not u.username and not u.password and not u.query and not u.fragment,
            'credentials/query must not occur in repository URL')
    require(host not in {'localhost', 'mau2', 'server2', '192.168.0.162', '192.168.0.10'}
            and not host.endswith('.invalid'), 'invalid/in-scope destination required')
    addresses = {x[4][0] for x in socket.getaddrinfo(host, u.port or 443)}
    require(addresses, 'destination unresolved')
    for address in addresses:
        ip = ipaddress.ip_address(address)
        require(not ip.is_loopback and not ip.is_unspecified and not ip.is_multicast
                and str(ip) not in {'192.168.0.162', '192.168.0.10'}, 'forbidden destination address')
    require(c.get('repository_id') and len(c['repository_id']) == 64,
            'pinned initialized repository ID required')
    require(isinstance(c.get('max_age_seconds'), int) and c['max_age_seconds'] > 0,
            'positive freshness limit required')
    require(not c.get('application_contracts'),
            'BLOCKED: app contracts need reviewed exporters; raw PVC backup is not implemented')
    ca = Path(c.get('ca_cert', ''))
    require(ca.is_file(), 'explicit trusted CA certificate missing')
    return c


def client(c):
    credentials = Path(os.environ.get('CREDENTIALS_DIRECTORY', '/nonexistent'))
    names = ['repository-password', 'rest-user', 'rest-password']
    for name in names:
        private_file(credentials / name)
    # Never inherit backend overrides/password commands or CLI secret arguments.
    env = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
           'HOME': '/root', 'LANG': 'C.UTF-8',
           'RESTIC_REPOSITORY': c['repository'],
           'RESTIC_PASSWORD_FILE': str(credentials / names[0]),
           'RESTIC_REST_USERNAME': (credentials / names[1]).read_text().strip(),
           'RESTIC_REST_PASSWORD': (credentials / names[2]).read_text().strip()}
    require(env['RESTIC_REST_USERNAME'] and env['RESTIC_REST_PASSWORD'], 'empty REST authentication')
    return env


def run_restic(c, env, *args):
    result = subprocess.run(['restic', '--no-cache', '--cacert', c['ca_cert'], *args],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=1200, check=False)
    require(result.returncode == 0, 'repository operation failed (including incomplete backups)')
    return result.stdout


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def recovery_inventory():
    require(TOKEN.is_file() and TLS.is_dir(), 'mandatory token/TLS material missing')
    # Files only; reject TLS symlinks rather than following outside the allowlist.
    files = [TOKEN]
    for p in sorted(TLS.rglob('*')):
        require(not p.is_symlink(), 'TLS symlink requires explicit review')
        if p.is_file():
            files.append(p)
    require(len(files) > 1, 'empty TLS recovery set')
    return {str(p): digest(p) for p in files}


def snapshot(c, env, path, tag):
    raw = run_restic(c, env, 'backup', '--json', '--host', 'mau2', '--tag', tag,
                     str(path))
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    ids = [r['snapshot_id'] for r in records if r.get('message_type') == 'summary'
           and r.get('snapshot_id')]
    require(len(ids) == 1, 'missing successful snapshot summary')
    run_restic(c, env, 'cat', 'snapshot', ids[0])
    return ids[0]


def export_sqlite(target):
    require(DB.is_file() and not DB.is_symlink(), 'SQLite source missing/unsafe')
    deadline = time.monotonic() + 120

    def progress(*_):
        require(time.monotonic() < deadline, 'SQLite export timeout')

    # Online Backup API includes committed WAL, no immutable mode or raw cp.
    with closing(sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True, timeout=5)) as source:
        with closing(sqlite3.connect(target)) as clone:
            source.backup(clone, pages=256, progress=progress, sleep=0.1)
            require(clone.execute('PRAGMA journal_mode=DELETE').fetchone() == ('delete',),
                    'standalone clone journal mode failed')
            require(clone.execute('PRAGMA integrity_check').fetchall() == [('ok',)],
                    'SQLite clone integrity failed')
    os.chmod(target, 0o600)


def backup(c, env):
    mounted = subprocess.run(['findmnt', '-n', '-M', str(STAGE), '-o', 'FSTYPE,OPTIONS'],
                             capture_output=True, text=True, check=True).stdout.split()
    require(len(mounted) == 2 and mounted[0] == 'tmpfs' and 'noswap' in mounted[1].split(','),
            'BLOCKED: private non-swapping tmpfs is required; no disk fallback')
    require(STAGE.stat().st_uid == 0 and not STAGE.stat().st_mode & 0o077,
            'unsafe staging permissions')
    version = subprocess.run(['/usr/local/bin/k3s', '--version'], capture_output=True,
                             text=True, timeout=10, check=True).stdout.splitlines()[0]
    # Scoped cleanup: TemporaryDirectory removes only this newly-created export.
    with tempfile.TemporaryDirectory(prefix='generation-', dir=STAGE) as directory:
        generation = Path(directory)
        before = recovery_inventory()
        export_sqlite(generation / 'state.db')
        for source in before:
            dest = generation / 'recovery' / source.lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o600)
            require(digest(dest) == before[source], 'recovery material changed during export')
        require(before == recovery_inventory(), 'token/TLS rotation overlapped backup')
        # Config allowlist, never whole server tree or live DB/WAL files.
        selected = [Path('/etc/rancher/k3s'), Path('/etc/ssh'), Path('/etc/ufw'),
                    Path('/etc/netplan'), Path('/etc/systemd/system/k3s.service'),
                    Path('/etc/systemd/system/k3s.service.env')]
        missing = []
        for source in selected:
            if not source.exists():
                missing.append(str(source))
                continue
            dest = generation / 'host-config' / str(source).lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if source.is_dir():
                shutil.copytree(source, dest, symlinks=True)
            else:
                shutil.copyfile(source, dest)
        manifest = {'format': 1, 'created_at': int(time.time()), 'k3s_version': version,
                    'sqlite_sha256': digest(generation / 'state.db'),
                    'recovery_hashes': before, 'missing_optional_config': missing,
                    'scope': 'k3s-and-selected-host-config-only', 'apps_protected': False}
        (generation / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # Stable snapshot paths for retention; generation ID lives in metadata.
        batch = STAGE / 'cluster'
        require(not batch.exists(), 'unexpected staging batch')
        generation.rename(batch)
        try:
            sid = snapshot(c, env, batch, 'server2-cluster-candidate')
            receipt = STAGE / 'receipt.json'
            receipt.write_text(json.dumps({'snapshot_id': sid, 'created_at': int(time.time()),
                                          'manifest_sha256': digest(batch / 'manifest.json')}) + '\n')
            receipt_id = snapshot(c, env, receipt, 'server2-cluster-receipt')
            status = STATE / 'last-success.json'
            temporary = STATE / 'last-success.new'
            temporary.write_text(json.dumps({'snapshot_id': sid, 'receipt_id': receipt_id,
                                              'created_at': int(time.time())}) + '\n')
            temporary.replace(status)
        finally:
            shutil.rmtree(batch)
            (STAGE / 'receipt.json').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'check', 'status', 'validate-config'])
    args = parser.parse_args()
    os.umask(0o077)
    require(os.geteuid() == 0 and socket.gethostname() == 'mau2', 'server2 root execution required')
    c = configuration()
    if args.action == 'validate-config':
        print('READY: configuration shape validated; credentials/backend/restore UNTESTED')
        return
    require(STATE.is_dir() and STATE.stat().st_uid == 0 and not STATE.stat().st_mode & 0o077,
            'private status/lock directory required')
    if args.action == 'status':
        status = json.loads((STATE / 'last-success.json').read_text())
        age = int(time.time()) - status['created_at']
        require(0 <= age <= c['max_age_seconds'], 'backup missing/stale or clock invalid')
        print('Backup freshness within configured limit; restore remains UNTESTED')
        return
    with (STATE / 'operation.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        env = client(c)
        repo = json.loads(run_restic(c, env, 'cat', 'config'))
        require(repo.get('id') == c['repository_id'], 'repository identity mismatch')
        if args.action == 'backup':
            backup(c, env)
        else:
            run_restic(c, env, 'check')
        print('Operation succeeded; no claim of tested end-to-end restore')


if __name__ == '__main__':
    try:
        main()
    except Blocked as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
    except Exception:
        # Avoid paths, backend responses and possibly sensitive exception strings.
        print('Backup operation failed; detailed output suppressed', file=sys.stderr)
        sys.exit(1)
