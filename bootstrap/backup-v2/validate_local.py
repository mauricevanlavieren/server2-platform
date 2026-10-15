#!/usr/bin/env python3
"""Local validation only; never invokes playbooks in deployment mode or systemctl."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import yaml
from jinja2 import Environment, StrictUndefined
ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT/'bootstrap/ansible/roles/backup_v2'

def run(command, **kwargs):
    p=subprocess.run(command,capture_output=True,text=True,**kwargs)
    if p.returncode:
        print(p.stdout); print(p.stderr); raise SystemExit(p.returncode)
    return p.stdout

def main():
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    print(run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'bootstrap/backup-v2/tests'),'-v'],env=env))
    for path in [*ROLE.rglob('*.py'),*ROOT.joinpath('bootstrap/recovery').glob('*.py')]:
        ast.parse(path.read_text())
    for path in [ROOT/'bootstrap/ansible/backup-v2-prepare.yml',*ROLE.rglob('*.yml')]:
        yaml.safe_load(path.read_text())
    run(['sh','-n',str(ROLE/'files/server3_backup_forced.sh')])
    defaults=yaml.safe_load((ROLE/'defaults/main.yml').read_text())
    jinja=Environment(undefined=StrictUndefined)
    jinja.filters['to_json']=json.dumps
    with tempfile.TemporaryDirectory(prefix='backup-v2-validation-') as t:
        temp=Path(t)
        for path in (ROLE/'templates').iterdir():
            result=jinja.from_string(path.read_text()).render(**defaults)
            if path.name.endswith('.json.j2'): json.loads(result)
            (temp/path.name.removesuffix('.j2')).write_text(result)
        # No deployment and no package installation. Syntax check only.
        ae=dict(env,ANSIBLE_LOCAL_TEMP=str(temp/'ansible-local'))
        run(['ansible-playbook','--syntax-check','-i','server2,',str(ROOT/'bootstrap/ansible/backup-v2-prepare.yml')],env=ae,cwd=ROOT/'bootstrap/ansible')
        run(['visudo','-c','-f',str(temp/'server3-backup-control.sudoers')])
        units=list(temp.glob('*.service'))+list(temp.glob('*.timer'))
        for unit in units:
            text=unit.read_text()
            assert '[Install]' not in text
            # Verify syntax against the available local interpreter; do not install
            # the proposed production executable or invoke a unit.
            unit.write_text(text.replace('/usr/local/sbin/server2-backup-v2',sys.executable))
        run(['systemd-analyze','verify',*map(str,units)])
        c=json.loads((temp/'config.json').read_text())
        for k in ['enabled','runtime_release_approved','inventory_handoff_approved','wol_enabled','allow_application_pause','retention_enabled','shutdown_enabled']:
            assert c[k] is False
        out=run([sys.executable,str(ROLE/'files/server2_backup.py'),'plan','--config',str(temp/'config.json')],env=env)
        assert json.loads(out)['enabled'] is False
        tasks=yaml.safe_load((ROLE/'tasks/main.yml').read_text())
        forbidden={'ansible.builtin.user','ansible.posix.authorized_key','ansible.builtin.systemd','ansible.builtin.systemd_service','ansible.builtin.command','ansible.builtin.shell','ansible.builtin.apt'}
        assert not any(forbidden.intersection(task) for task in tasks)
    print('PASS: unit tests, AST, YAML, Jinja/JSON, shell syntax, Ansible syntax, sudoers syntax, systemd syntax, disabled defaults and no deployment/access tasks.')
    return 0
if __name__=='__main__': raise SystemExit(main())
