#!/usr/bin/env python3
"""Backup v2 review implementation. Default disabled; no pause/delete/power actions."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import sqlite3
import stat
import subprocess
import time
import uuid

REPO = 'sftp:backupsvc@192.168.0.186:/backup/restic'
REPO_ID = '00c5600469b3306c939434a0e232fb141e844a3931a307a1c0af58e5066fed68'
FS_UUID = '67837227-f008-4257-822a-b4562efa2daa'
DATASETS = {'k3s', 'forgejo', 'inventory', 'postkamer', 'recovery'}

class Blocked(RuntimeError):
    pass

def require(ok, message):
    if not ok:
        raise Blocked(message)

def strict_bool(value):
    return type(value) is bool and value is True

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def private_file(path, owner=0):
    p = Path(path)
    s = p.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == owner and not s.st_mode & 0o077,
            'unsafe credential/configuration metadata')
    require(p.resolve() == p, 'symlinked credential/configuration path')

def atomic_json(path, data):
    p = Path(path)
    temp = p.with_name(p.name + '.' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, p)
    finally:
        if temp.exists():
            temp.unlink()

def sqlite_info(path):
    with contextlib.closing(sqlite3.connect(Path(path).as_uri() + '?mode=ro', uri=True, timeout=5)) as db:
        db.execute('PRAGMA query_only=ON')
        require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'SQLite integrity failure')
        require(not db.execute('PRAGMA foreign_key_check').fetchall(), 'SQLite foreign key failure')
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {n: db.execute('SELECT count(*) FROM "' + n.replace('"', '""') + '"').fetchone()[0] for n in names}

def online_export(source, target, guard, seconds=60):
    deadline = time.monotonic() + seconds
    def progress(status, remaining, total):
        guard()
        require(time.monotonic() < deadline, 'SQLite export timeout')
    with contextlib.closing(sqlite3.connect(Path(source).as_uri() + '?mode=ro', uri=True, timeout=5)) as src:
        src.execute('PRAGMA query_only=ON')
        with contextlib.closing(sqlite3.connect(target)) as dst:
            src.backup(dst, pages=16, progress=progress, sleep=0.05)
    return sqlite_info(target)

def tree_manifest(root):
    root = Path(root)
    result = {}
    for p in sorted(root.rglob('*')):
        s = p.lstat()
        require(stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode), 'unsupported link/device in recovery tree')
        if p.is_file():
            result[str(p.relative_to(root))] = {'sha256': sha(p), 'bytes': s.st_size,
                                               'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid}
    return result

def safe_config(c):
    require(c.get('repository') == REPO and c.get('repository_id') == REPO_ID and
            c.get('filesystem_uuid') == FS_UUID, 'target identity mismatch')
    for name in ['retention_enabled', 'shutdown_enabled', 'allow_application_pause']:
        require(c.get(name) is False, 'unsupported destructive/pause capability requested')
    require(c.get('control_host') == '192.168.0.186' and c.get('source_host') == 'mau2', 'host mismatch')
    require(c.get('wol_broadcast') == '192.168.0.255' and
            c.get('wol_mac') == '20:cf:30:7f:56:f8', 'WoL identity mismatch')
    require(set(c.get('contracts', {})) == DATASETS, 'incomplete dataset inventory')
    return c

def runtime_ready(c):
    safe_config(c)
    require(strict_bool(c.get('enabled')), 'backup disabled')
    require(strict_bool(c.get('runtime_release_approved')), 'runtime release not approved')
    kinds = {'k3s': 'k3s-coherent', 'forgejo': 'forgejo-fenced',
             'inventory': 'sqlite', 'postkamer': 'sqlite', 'recovery': 'independent-recovery'}
    for name, contract in c['contracts'].items():
        require(strict_bool(contract.get('approved')) and contract.get('kind') == kinds[name],
                'dataset contract not approved: ' + name)
    require(strict_bool(c.get('inventory_handoff_approved')), 'legacy timer handoff not approved')
    require(c.get('stage') == '/run/server2-backup-v2' and
            c.get('status_file') == '/var/lib/server2-backup-v2/status.json', 'unsafe runtime paths')


def magic_packet(mac):
    require(mac == '20:cf:30:7f:56:f8', 'unexpected wake target')
    return b'\xff' * 6 + bytes.fromhex(mac.replace(':', '')) * 16

def wake(c):
    require(strict_bool(c.get('enabled')) and strict_bool(c.get('wol_enabled')), 'WoL disabled')
    safe_config(c)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet(c['wol_mac']), (c['wol_broadcast'], 9))

class Control:
    """Persistent restricted SSH session. Lease never survives loss of freshness."""
    def __init__(self, c):
        self.p = subprocess.Popen(['ssh', '-F', '/dev/null', '-T', '-i', c['control_key'], '-o', 'IdentitiesOnly=yes',
            '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + c['known_hosts'],
            '-o', 'ConnectTimeout=8', '-o', 'ServerAliveInterval=3', '-o', 'ServerAliveCountMax=2',
            'backupctl@192.168.0.186', 'server3-backup-control'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        self.run_id = uuid.uuid4().hex
        self.boot_id = None
        self.last = 0
    def request(self, operation):
        body = json.dumps({'op': operation, 'run': self.run_id, 'boot_id': self.boot_id}).encode() + b'\n'
        self.p.stdin.write(body)
        self.p.stdin.flush()
        deadline = time.monotonic() + 8
        raw = bytearray()
        while b'\n' not in raw:
            require(time.monotonic() < deadline, 'control timeout')
            ready, _, _ = select.select([self.p.stdout], [], [], max(0, deadline - time.monotonic()))
            require(ready, 'control timeout')
            chunk = os.read(self.p.stdout.fileno(), 1)
            require(chunk, 'control disconnected')
            raw.extend(chunk)
            require(len(raw) <= 4096, 'oversized control reply')
        try:
            reply = json.loads(raw)
        except ValueError:
            raise Blocked('invalid control reply') from None
        require(reply.get('ok') is True and reply.get('uuid') == FS_UUID and reply.get('host') == 'mau3', 'guard rejected')
        require(reply.get('run') == self.run_id, 'control run mismatch')
        boot = reply.get('boot_id')
        require(isinstance(boot, str) and (self.boot_id is None or boot == self.boot_id), 'server3 rebooted')
        self.boot_id = boot
        self.last = time.monotonic()
        return reply
    def tick(self):
        if time.monotonic() - self.last >= 5:
            self.request('lease-renew')
    def close(self):
        if self.p.poll() is None:
            self.p.terminate()
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()

class Restic:
    ALLOWED = {'cat', 'list', 'snapshots', 'backup', 'restore', 'check'}
    def __init__(self, c, guard):
        self.guard = guard
        ssh = ['ssh', '-F', '/dev/null', '-i', c['sftp_key'], '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + c['known_hosts'],
               '-o', 'ConnectTimeout=8', 'backupsvc@192.168.0.186', '-s', 'sftp']
        import shlex
        self.argv = ['restic', '--repo', REPO, '--password-file', c['password_file'], '--no-cache',
                     '-o', 'sftp.command=' + shlex.join(ssh)]
    def call(self, operation, *args):
        require(operation in self.ALLOWED, 'Restic operation forbidden')
        # Options are exclusively constructed by the engine, never by SSH requests.
        self.guard()
        extra = ['--no-lock'] if operation in {'cat', 'list', 'snapshots'} else []
        p = subprocess.Popen(self.argv + extra + [operation, *args], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env={'PATH': '/usr/bin:/bin', 'HOME': '/root', 'LANG': 'C.UTF-8'})
        deadline = time.monotonic() + 1800
        try:
            while True:
                try:
                    out, err = p.communicate(timeout=1)
                    break
                except subprocess.TimeoutExpired:
                    self.guard()
                    require(time.monotonic() < deadline, 'Restic timeout')
            require(p.returncode == 0, 'Restic failed; diagnostics suppressed')
            self.guard()
            return out
        except BaseException:
            p.terminate()
            try:
                p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate()
            raise
    def backup(self, root, dataset, run_id):
        raw = self.call('backup', '--json', '--host', 'mau2', '--tag', 'backup-v2',
                        '--tag', 'dataset:' + dataset, '--tag', 'run:' + run_id, str(root))
        ids = [r['snapshot_id'] for r in map(json.loads, raw.splitlines())
               if r.get('message_type') == 'summary' and r.get('snapshot_id')]
        require(len(ids) == 1 and re.fullmatch('[a-f0-9]{64}', ids[0]), 'missing successful snapshot')
        return ids[0]

def sqlite_candidate(contract, root, run_id, dataset, guard):
    root = Path(root)
    require(not any(root.iterdir()), 'export location not empty')
    source = Path(contract['source'])
    require(source.resolve() == source and source.is_file(), 'unsafe/missing source')
    # Refuse unexpected sidefiles. Journal/WAL/SHM are handled by SQLite itself.
    allowed = {source.name, source.name + '-wal', source.name + '-shm', source.name + '-journal'}
    require(all(p.name in allowed and p.is_file() and not p.is_symlink() for p in source.parent.iterdir()),
            'unexpected persistent sidefiles; contract must be revised')
    counts = online_export(source, root / 'database.sqlite', guard)
    metadata = {'run': run_id, 'dataset': dataset, 'method': 'sqlite-online', 'contract_version': 1,
                'table_counts': counts, 'source_identity': contract['source_identity']}
    atomic_json(root / 'manifest.json', metadata)
    return tree_manifest(root)

def verify_forgejo_tree(payload):
    payload = Path(payload)
    sqlite_info(payload / 'data/forgejo.db')
    require((payload / 'custom/conf/app.ini').is_file() and (payload / 'git/repositories').is_dir(),
            'Forgejo DB/config/repository set incomplete')
    for repo in (payload / 'git/repositories').rglob('*.git'):
        require(repo.is_dir() and not repo.is_symlink(), 'unsafe Git repository')
        require(not (repo / 'objects/info/alternates').exists(), 'external Git alternates refused')
        result = subprocess.run(['git', '--no-replace-objects', '-c', 'core.fsmonitor=false',
            '-c', 'core.hooksPath=/dev/null', '-c', 'safe.directory=' + str(repo),
            '--git-dir=' + str(repo), 'fsck', '--full', '--strict'],
            capture_output=True, timeout=60, env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
                                              'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'})
        require(result.returncode == 0, 'restored Git repository integrity failed')

def verify_recovery_tree(payload):
    payload = Path(payload)
    d = json.loads((payload / 'recovery-inventory.json').read_text())
    required = {'git-bundle', 'host-bootstrap', 'images', 'secrets-escrow', 'dataset-contracts'}
    require(set(d.get('components', {})) == required and
            all(v.get('verified') is True for v in d['components'].values()), 'restored recovery inventory incomplete')
    files = tree_manifest(payload)
    files.pop('recovery-inventory.json', None)
    require(files == d['files'], 'restored recovery artifact mismatch')


def verify_candidate(restic, sid, expected, destination):
    restic.call('restore', sid, '--target', str(destination), '--verify')
    # Stable export directory is named export. Restic retains its absolute hierarchy.
    dirs = [p.parent for p in Path(destination).rglob('manifest.json') if p.parent.name == 'export']
    require(len(dirs) == 1, 'unexpected restore layout')
    restored = dirs[0]
    require(tree_manifest(restored) == expected, 'restored files differ')
    metadata = json.loads((restored / 'manifest.json').read_text())
    if metadata['method'] in {'sqlite-online', 'k3s-online'}:
        require(sqlite_info(restored / 'database.sqlite') == metadata['table_counts'], 'restored tables differ')
    if metadata.get('dataset') == 'forgejo':
        verify_forgejo_tree(restored / 'payload')
    elif metadata.get('dataset') == 'recovery':
        verify_recovery_tree(restored / 'payload')
    return metadata

def verified_bundle(restic, prepared, receipt_dir, run_id):
    """Port-based coordinator: only fully verified candidates may get a receipt.

    Production CLI is gated until all contracts and runtime release
    have passed separate review. This engine is integration-tested
    locally with synthetic datasets and an in-memory repository port.
    """
    require(set(prepared) == DATASETS, 'bundle missing dataset')
    ids = {}
    for dataset in sorted(DATASETS):
        item = prepared[dataset]
        ids[dataset] = restic.backup(item['export'], dataset, run_id)
        verify_candidate(restic, ids[dataset], item['manifest'], item['restore'])
    restic.call('check', '--read-data')
    receipt = {'run': run_id, 'status': 'verified', 'candidates': ids,
               'manifest_hashes': {n: hashlib.sha256(json.dumps(prepared[n]['manifest'], sort_keys=True).encode()).hexdigest() for n in DATASETS}}
    atomic_json(Path(receipt_dir) / 'receipt.json', receipt)
    rid = restic.backup(receipt_dir, 'receipt', run_id)
    # Read receipt back from encrypted repository, do not trust backup exit alone.
    probe = Path(receipt_dir).parent / 'receipt-restore'
    require(not probe.exists(), 'receipt restore target exists')
    probe.mkdir(mode=0o700)
    restic.call('restore', rid, '--target', str(probe), '--verify')
    receipts = list(probe.rglob('receipt.json'))
    require(len(receipts) == 1 and json.loads(receipts[0].read_text()) == receipt, 'receipt verification failed')
    return {**receipt, 'receipt_id': rid}

def inventory_paths(paths):
    result = {}
    for text in paths:
        p = Path(text)
        require(p.is_absolute() and p.resolve() == p, 'unsafe recovery path')
        require(p.is_file() or p.is_dir(), 'missing recovery dependency')
        files = [p] if p.is_file() else sorted(p.rglob('*'))
        for item in files:
            mode = item.lstat().st_mode
            require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), 'recovery symlink/device refused')
            if item.is_file():
                st = item.stat()
                result[str(item)] = {'sha256': sha(item), 'mode': stat.S_IMODE(mode),
                                     'uid': st.st_uid, 'gid': st.st_gid, 'bytes': st.st_size}
    return result

def k3s_candidate(contract, root, run_id, guard):
    root = Path(root)
    require(contract.get('encryption_inventory_verified') is True and
            contract.get('rotation_interlock_verified') is True,
            'k3s key inventory/rotation interlock not validated')
    required = {'/var/lib/rancher/k3s/server/token', '/var/lib/rancher/k3s/server/tls',
                '/etc/rancher/k3s/config.yaml'}
    paths = contract.get('recovery_paths', [])
    require(required.issubset(set(paths)), 'incomplete k3s recovery set')
    require(not any(root.iterdir()), 'export location not empty')
    source = Path(contract['source'])
    require(str(source) == '/var/lib/rancher/k3s/server/db/state.db' and source.resolve() == source, 'unexpected k3s database path')
    before = inventory_paths(paths)
    counts = online_export(contract['source'], root / 'database.sqlite', guard)
    for source in before:
        target = root / 'recovery-files' / source.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(source, target)
        require(sha(target) == before[source]['sha256'], 'recovery file changed during copy')
    require(inventory_paths(paths) == before, 'key/config rotation overlapped export')
    atomic_json(root / 'manifest.json', {'run': run_id, 'dataset': 'k3s', 'method': 'k3s-online',
                'contract_version': 1, 'table_counts': counts, 'source_identity': contract['source_identity'],
                'recovery_inventory': before})
    return tree_manifest(root)

def sealed_candidate(contract, root, run_id, dataset, guard):
    """Consume, never create, a separately audited writer-fenced/recovery export.

    A root-only receipt is a trust boundary, not proof that writers were stopped.
    Its producer/watchdog must be separately approved and integration-tested.
    No code here pauses applications or gathers secret material implicitly.
    """
    require(contract.get('producer_reviewed') is True, 'sealed-export producer not approved')
    source = Path(contract['sealed_export'])
    require(str(source).startswith('/run/server2-sealed-exports/') and source.resolve() == source,
            'only private prepared exports accepted; never a live PVC')
    receipt_path = source / 'seal.json'
    private_file(receipt_path)
    receipt_hash = sha(receipt_path)
    seal = json.loads(receipt_path.read_text())
    require(seal.get('dataset') == dataset and seal.get('source_identity') == contract['source_identity'] and
            seal.get('producer_contract') == contract['producer_contract'], 'sealed export identity mismatch')
    require(seal.get('verified') is True and time.time() <= seal['expires_at'] <= time.time() + 3600,
            'unverified/expired export')
    if dataset == 'forgejo':
        require(seal.get('writers_fenced') is True and seal.get('resume_watchdog_active') is True,
                'Forgejo writer fence/watchdog missing')
    else:
        require(seal.get('offline_git_verified') is True and seal.get('image_escrow_verified') is True and
                seal.get('independent_credentials_confirmed') is True, 'recovery set incomplete')
    # A separately approved producer owns this independent private noswap mount.
    require(source.stat().st_uid == 0 and stat.S_IMODE(source.stat().st_mode) == 0o700, 'unsafe sealed-export directory')
    probe = subprocess.run(['findmnt', '--json', '--target', str(source), '-o', 'TARGET,FSTYPE,OPTIONS'], capture_output=True, timeout=5)
    require(probe.returncode == 0, 'sealed export mount not verified')
    mount = json.loads(probe.stdout)['filesystems'][0]
    require(mount['fstype'] == 'tmpfs' and 'noswap' in mount['options'].split(','), 'sealed export needs noswap tmpfs')
    expected = seal['files']
    actual = tree_manifest(source)
    actual.pop('seal.json', None)
    require(actual == expected, 'sealed export content mismatch')
    for rel in expected:
        guard()
        src = source / rel
        require(src.resolve().is_relative_to(source) and src.is_file(), 'unsafe sealed relative path')
        dst = Path(root) / 'payload' / rel
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        require(sha(dst) == expected[rel]['sha256'], 'sealed export changed')
    require(sha(receipt_path) == receipt_hash and time.time() <= seal['expires_at'], 'seal expired/changed during copy')
    guard()
    atomic_json(Path(root) / 'manifest.json', {'run': run_id, 'dataset': dataset, 'method': 'sealed-tree',
                'contract_version': 1, 'source_identity': contract['source_identity'],
                'producer_contract': contract['producer_contract'], 'seal_sha256': receipt_hash})
    return tree_manifest(root)

def estimated_stage_bytes(c):
    total = 0
    count = 0
    for name, contract in c['contracts'].items():
        if contract['kind'] in {'sqlite', 'k3s-coherent'}:
            p = Path(contract['source'])
            for f in [p, Path(str(p) + '-wal'), Path(str(p) + '-journal')]:
                if f.exists():
                    require(f.is_file() and not f.is_symlink(), 'unsafe source file')
                    total += f.stat().st_size
                    count += 1
            if contract['kind'] == 'k3s-coherent':
                inv = inventory_paths(contract['recovery_paths'])
                total += sum(d['bytes'] for d in inv.values())
                count += len(inv)
        else:
            source = Path(contract['sealed_export'])
            require(str(source).startswith('/run/server2-sealed-exports/') and source.resolve() == source,
                    'unsafe prepared export')
            inv = tree_manifest(source)
            total += sum(d['bytes'] for d in inv.values())
            count += len(inv)
    return 3 * (total + count * 4096) + 16*1024*1024


def stage_safety(c):
    stage = Path(c['stage'])
    require(stage.resolve() == stage and stage.stat().st_uid == 0 and
            stat.S_IMODE(stage.stat().st_mode) == 0o700, 'unsafe staging directory')
    p = subprocess.run(['findmnt', '--json', '--mountpoint', str(stage), '-o', 'TARGET,FSTYPE,OPTIONS'],
                       capture_output=True, timeout=5)
    require(p.returncode == 0, 'staging mount absent')
    mount = json.loads(p.stdout)['filesystems'][0]
    require(mount['fstype'] == 'tmpfs' and 'noswap' in mount['options'].split(','), 'non-swapping tmpfs required')
    mem = {l.split(':')[0]: int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()
           if l.startswith(('MemAvailable:', 'MemTotal:'))}
    cap = os.statvfs(stage).f_blocks * os.statvfs(stage).f_frsize
    require(cap <= mem['MemAvailable']//8 and mem['MemAvailable']-cap >= 512*1024*1024,
            'unsafe memory reservation')
    required = max(c['stage_required_bytes'], estimated_stage_bytes(c))
    require(type(required) is int and required >= 16*1024*1024 and
            shutil.disk_usage(stage).free > required, 'insufficient export/restore budget')
    return stage

def ensure_legacy_inactive():
    for unit in ['it-discovery-backup.timer', 'it-discovery-backup.service']:
        p = subprocess.run(['systemctl', 'show', '--no-pager',
                            '--property=LoadState,ActiveState,UnitFileState', unit], capture_output=True)
        require(p.returncode == 0, 'cannot reliably inspect legacy Inventory units')
        fields = dict(line.split('=', 1) for line in p.stdout.decode().splitlines() if '=' in line)
        require(fields.get('LoadState') in {'loaded', 'not-found'} and fields.get('ActiveState') == 'inactive',
                'legacy Inventory unit running, transitioning or not established')
        if fields['LoadState'] == 'loaded' and unit.endswith('.timer'):
            require(fields.get('UnitFileState') in {'disabled', 'masked'}, 'legacy Inventory timer still enabled')


def production_backup(c):
    runtime_ready(c)  # no IO before explicit release
    require(os.geteuid() == 0 and socket.gethostname().split('.')[0] == 'mau2', 'wrong execution identity')
    for name in ['password_file', 'sftp_key', 'control_key', 'known_hosts']:
        private_file(c[name], owner=0 if name != 'sftp_key' else os.stat('/home/mau').st_uid)
    ensure_legacy_inactive()
    stage = stage_safety(c)
    run_id = uuid.uuid4().hex
    state = Path('/var/lib/server2-backup-v2')
    require(state.resolve() == state and state.stat().st_uid == 0 and stat.S_IMODE(state.stat().st_mode) == 0o700, 'unsafe status directory')
    fd = os.open(state / 'run.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not any(stage.iterdir()), 'previous staging retained; operator review required')
        atomic_json(c['status_file'], {'status': 'running', 'run': run_id, 'started_at': time.time()})
        ctl = None
        try:
            # Only bounded wake attempts. Failed SSH is never treated as proof of power ownership.
            for attempt in range(4):
                try:
                    ctl = Control(c)
                    ctl.request('check')
                    break
                except (Blocked, OSError):
                    if ctl is not None:
                        ctl.close()
                    ctl = None
                    require(attempt < 3 and c['wol_enabled'] is True, 'server3 unavailable; no fallback')
                    wake(c)
                    time.sleep(10 * (attempt + 1))
            ctl.run_id = run_id
            ctl.request('lease-acquire')
            restic = Restic(c, ctl.tick)
            config = json.loads(restic.call('cat', 'config'))
            require(config.get('id') == REPO_ID, 'repository ID mismatch')
            require(not restic.call('list', 'locks').strip(), 'repository already locked')
            prepared = {}
            for name, contract in sorted(c['contracts'].items()):
                ctl.tick()
                folder = stage / name
                folder.mkdir(mode=0o700)
                export, restore = folder / 'export', folder / 'restore'
                export.mkdir(mode=0o700)
                restore.mkdir(mode=0o700)
                if contract['kind'] == 'sqlite':
                    inventory = sqlite_candidate(contract, export, run_id, name, ctl.tick)
                elif contract['kind'] == 'k3s-coherent':
                    inventory = k3s_candidate(contract, export, run_id, ctl.tick)
                else:
                    inventory = sealed_candidate(contract, export, run_id, name, ctl.tick)
                prepared[name] = {'export': export, 'restore': restore, 'manifest': inventory}
            receipt_dir = stage / 'receipt'
            receipt_dir.mkdir(mode=0o700)
            result = verified_bundle(restic, prepared, receipt_dir, run_id)
            # No new success before verification AND sensitive staging cleanup complete.
            for name in [*DATASETS, 'receipt', 'receipt-restore']:
                shutil.rmtree(stage / name)
            ctl.request('lease-release')
            atomic_json(c['status_file'], {**result, 'verified_at': time.time()})
            return {'status': 'verified', 'run': run_id, 'receipt_id': result['receipt_id']}
        except BaseException:
            atomic_json(c['status_file'], {'status': 'failed', 'run': run_id, 'failed_at': time.time(),
                                         'detail': 'unverified staging must never be reused; tmpfs owner controls its lifecycle'})
            raise
        finally:
            if ctl is not None:
                ctl.close()


def freshness(c, now=None):
    require(strict_bool(c.get('enabled')), 'backup disabled; status is not healthy')
    p = Path(c['status_file'])
    s = json.loads(p.read_text())
    age = (time.time() if now is None else now) - s['verified_at']
    require(s.get('status') == 'verified' and set(s.get('candidates', {})) == DATASETS and
            isinstance(s.get('receipt_id'), str) and 0 <= age <= c['max_age_seconds'], 'backup missing/partial/stale')
    return {'status': 'fresh', 'age_seconds': int(age)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['plan', 'backup', 'status'])
    parser.add_argument('--config', default='/etc/server2-backup-v2/config.json')
    args = parser.parse_args()
    try:
        if args.action != 'plan':
            private_file(args.config)
        c = safe_config(json.loads(Path(args.config).read_text()))
        if args.action == 'plan':
            print(json.dumps({'enabled': c['enabled'], 'production_ready': False,
                              'adapters_pending': ['k3s-coherent-keys', 'forgejo-writer-fencing', 'independent-recovery-acquisition']}))
        elif args.action == 'status':
            print(json.dumps(freshness(c)))
        else:
            print(json.dumps(production_backup(c)))
    except Exception:
        print(json.dumps({'status': 'BLOCKED', 'detail': 'disabled, incomplete contract or failed safety check; no success recorded'}))
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
