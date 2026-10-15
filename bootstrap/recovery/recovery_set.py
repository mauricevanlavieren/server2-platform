#!/usr/bin/env python3
"""Offline recovery-set manifest review. Does not acquire/unseal credentials."""
import argparse
import hashlib
import json
import ipaddress
from pathlib import Path
import sys

REQUIRED = {'restic-decrypt', 'sftp-read-access', 'server3-hostkey', 'sops-age', 'ca-recovery',
            'github-recovery', 'git-bundle', 'host-bootstrap', 'image-escrow', 'dataset-contracts', 'snapshot-receipts'}

def assess(manifest):
    if manifest.get('schema') != 1 or set(manifest.get('components', {})) != REQUIRED:
        raise ValueError('invalid recovery-set schema')
    # No inline credential values are accepted, even in a private manifest.
    def check(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in {'password', 'private_key', 'secret_value', 'token_value', 'passphrase'}:
                    raise ValueError('inline secret prohibited')
                check(v)
        elif isinstance(node, list):
            for v in node:
                check(v)
    check(manifest)
    missing = [n for n, d in manifest['components'].items()
               if d.get('independently_available') is not True or d.get('verified') is not True]
    target = manifest.get('server4', {})
    isolated = target.get('identity_confirmed') is True and target.get('isolated') is True
    if isolated:
        address = str(ipaddress.IPv4Address(target.get('ip')))
        if address in {'192.168.0.10', '192.168.0.162', '192.168.0.186'} or target.get('hostname') in {'mau2', 'mau3', 'server1'}:
            raise ValueError('unsafe recovery target')
    return {'ready_for_isolated_test': not missing and isolated and bool(manifest.get('artifacts')), 'missing_components': sorted(missing),
            'full_disaster_recovery_proven': False,
            'server4_identity_recorded': manifest.get('server4', {}).get('identity_confirmed') is True}

def verify_artifacts(manifest, root):
    root = Path(root).resolve()
    for entry in manifest.get('artifacts', []):
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not rel.parts:
            raise ValueError('unsafe artifact path')
        p = root / rel
        if p.resolve() != p or not p.is_file():
            raise ValueError('symlink or missing artifact')
        h = hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda: stream.read(1024*1024), b''):
                h.update(block)
        if h.hexdigest() != entry['sha256']:
            raise ValueError('artifact checksum failure')
    return len(manifest.get('artifacts', []))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['plan', 'verify'])
    parser.add_argument('manifest')
    parser.add_argument('--artifact-root')
    args = parser.parse_args()
    try:
        manifest = json.loads(Path(args.manifest).read_text())
        result = assess(manifest)
        if args.action == 'verify':
            if args.artifact_root is None:
                raise ValueError('artifact root required')
            result['artifact_files_verified'] = verify_artifacts(manifest, args.artifact_root)
            if result['artifact_files_verified'] == 0:
                result['ready_for_isolated_test'] = False
            result['ready_for_isolated_test'] &= result['server4_identity_recorded']
        print(json.dumps(result, sort_keys=True))
        return 0 if result['ready_for_isolated_test'] else 2
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({'status': 'BLOCKED', 'detail': 'manifest/artifact invalid; no secrets printed'}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
