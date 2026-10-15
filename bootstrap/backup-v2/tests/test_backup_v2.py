"""Synthetic local tests only. No SSH, sockets, credentials, mount or live DB."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[3]
ROLE = ROOT / 'bootstrap/ansible/roles/backup_v2'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
b = load('backup', ROLE/'files/server2_backup.py')
g = load('guard', ROLE/'files/server3_backup_control.py')
r = load('recovery', ROOT/'bootstrap/recovery/recovery_set.py')
def config():
    defaults = yaml.safe_load((ROLE/'defaults/main.yml').read_text())
    env = Environment(undefined=StrictUndefined)
    env.filters['to_json'] = json.dumps
    return json.loads(env.from_string((ROLE/'templates/config.json.j2').read_text()).render(**defaults))
def fixture(path):
    db = sqlite3.connect(path)
    db.executescript('CREATE TABLE messages(id INTEGER PRIMARY KEY, body TEXT); INSERT INTO messages(body) VALUES ("synthetic");')
    db.commit(); db.close()

class MemoryRepository:
    def __init__(self, root, fail_check=False, corrupt=False, corrupt_receipt=False):
        self.root=Path(root); self.snapshots={}; self.calls=[]
        self.fail_check=fail_check; self.corrupt=corrupt; self.corrupt_receipt=corrupt_receipt
    def backup(self, source, dataset, run):
        self.calls.append(('backup',dataset))
        sid=hashlib.sha256((dataset+str(len(self.snapshots))).encode()).hexdigest()
        dst=self.root/sid; shutil.copytree(source,dst)
        self.snapshots[sid]=(dst,str(source)); return sid
    def call(self, op, *args):
        self.calls.append((op,*args))
        if op=='check':
            b.require(not self.fail_check,'synthetic repository corruption'); return b''
        if op=='restore':
            sid=args[0]; target=Path(args[args.index('--target')+1]); stored,original=self.snapshots[sid]
            dst=target/original.lstrip('/'); dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(stored,dst)
            candidates=list(dst.rglob('database.sqlite'))+list(dst.rglob('forgejo.db'))
            if self.corrupt and candidates:
                candidates[0].write_bytes(b'corrupt synthetic data')
            if self.corrupt_receipt and (dst/'receipt.json').exists():
                (dst/'receipt.json').write_text('{}')
            return b''
        raise AssertionError('Unexpected operation')

class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='backup-v2-synthetic-')
        self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def test_defaults_all_off(self):
        c=config()
        for key in ['enabled','runtime_release_approved','wol_enabled','allow_application_pause','retention_enabled','shutdown_enabled']:
            self.assertIs(c[key],False)
        self.assertTrue(all(d['approved'] is False for d in c['contracts'].values()))
    def test_disabled_before_any_external_operation(self):
        with patch.object(b.subprocess,'Popen',side_effect=AssertionError('process attempted')),patch.object(b.socket,'socket',side_effect=AssertionError('network attempted')):
            with self.assertRaises(b.Blocked): b.production_backup(config())
    def test_no_release_even_if_enabled(self):
        c=config(); c['enabled']=True
        with self.assertRaises(b.Blocked): b.runtime_ready(c)
    def test_no_string_truthiness(self):
        c=config(); c['enabled']='true'
        with self.assertRaises(b.Blocked): b.runtime_ready(c)
    def test_target_cannot_be_server1(self):
        c=config(); c['repository']='sftp:backupsvc@192.168.0.10:/backup/restic'
        with self.assertRaises(b.Blocked): b.safe_config(c)
    def test_wrong_uuid(self):
        c=config(); c['filesystem_uuid']='wrong'
        with self.assertRaises(b.Blocked): b.safe_config(c)
    def test_no_power_retention_pause(self):
        for key in ['retention_enabled','shutdown_enabled','allow_application_pause']:
            c=config(); c[key]=True
            with self.assertRaises(b.Blocked): b.safe_config(c)
    def test_forbidden_restic_operations(self):
        restic=b.Restic(config(),lambda:None)
        with patch.object(b.subprocess,'Popen',side_effect=AssertionError('process attempted')):
            for op in ['forget','prune','unlock','init','repair']:
                with self.assertRaises(b.Blocked): restic.call(op)
    def test_legacy_handoff_refuses_existing_timer_or_running_service(self):
        failures=[(0,b'LoadState=loaded\nActiveState=inactive\nUnitFileState=enabled\n'),
                  (0,b'LoadState=loaded\nActiveState=active\nUnitFileState=disabled\n'),
                  (1,b''),(0,b'')]
        for code,body in failures:
            with self.subTest(code=code,body=body),patch.object(b.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=body)),self.assertRaises(b.Blocked):
                b.ensure_legacy_inactive()
    def test_legacy_handoff_checks_only_without_modification(self):
        reply=SimpleNamespace(returncode=0,stdout=b'LoadState=loaded\nActiveState=inactive\nUnitFileState=disabled\n')
        with patch.object(b.subprocess,'run',return_value=reply) as call:
            b.ensure_legacy_inactive()
            self.assertEqual(call.call_count,2)
            self.assertTrue(all(c.args[0][1]=='show' for c in call.call_args_list))
    def test_lock_listing_does_not_create_its_own_lock(self):
        process=SimpleNamespace(returncode=0,communicate=lambda timeout:(b'',b''))
        with patch.object(b.subprocess,'Popen',return_value=process) as call:
            b.Restic(config(),lambda:None).call('list','locks')
            args=call.call_args.args[0]
            self.assertLess(args.index('--no-lock'),args.index('list'))
    def test_wol_disabled(self):
        with patch.object(b.socket,'socket',side_effect=AssertionError('socket attempted')):
            with self.assertRaises(b.Blocked): b.wake(config())
    def test_magic_packet_pinned(self):
        self.assertEqual(len(b.magic_packet('20:cf:30:7f:56:f8')),102)
        with self.assertRaises(b.Blocked): b.magic_packet('00:00:00:00:00:00')
    def test_online_backup_preserves_source(self):
        src=self.root/'source.sqlite'; dst=self.root/'export.sqlite'; fixture(src)
        before=b.sha(src); info=b.online_export(src,dst,lambda:None)
        self.assertEqual(info,{'messages':1}); self.assertEqual(b.sha(src),before)
    def test_guard_loss_interrupts_export(self):
        src=self.root/'source.sqlite'; fixture(src); before=b.sha(src)
        def lost(): raise b.Blocked('synthetic guard loss')
        with self.assertRaises(b.Blocked): b.online_export(src,self.root/'out.sqlite',lost)
        self.assertEqual(b.sha(src),before)
    def test_online_export_during_wal_writes_is_transactionally_consistent(self):
        src=self.root/'live.sqlite'; out=self.root/'copy.sqlite'
        db=sqlite3.connect(src); db.execute('PRAGMA journal_mode=WAL')
        db.executescript('CREATE TABLE messages(id INTEGER PRIMARY KEY); CREATE TABLE counter(n INTEGER); INSERT INTO counter VALUES(0);')
        db.commit(); db.close()
        stop=threading.Event(); ready=threading.Event()
        def writer():
            c=sqlite3.connect(src)
            try:
                while not stop.is_set():
                    c.execute('INSERT INTO messages DEFAULT VALUES')
                    c.execute('UPDATE counter SET n=n+1'); c.commit(); ready.set(); time.sleep(0.002)
            finally: c.close()
        thread=threading.Thread(target=writer); thread.start()
        try:
            self.assertTrue(ready.wait(2))
            b.online_export(src,out,lambda:None)
            c=sqlite3.connect(out)
            try: self.assertEqual(c.execute('SELECT n FROM counter').fetchone()[0],c.execute('SELECT count(*) FROM messages').fetchone()[0])
            finally: c.close()
        finally: stop.set(); thread.join(2)
        self.assertFalse(thread.is_alive())
    def test_corrupt_database_rejected(self):
        p=self.root/'bad.sqlite'; p.write_bytes(b'invalid')
        with self.assertRaises(sqlite3.DatabaseError): b.sqlite_info(p)
    def test_unknown_pvc_sidefile_blocks(self):
        source=self.root/'source'; source.mkdir(); p=source/'db.sqlite'; fixture(p)
        (source/'attachment.txt').write_text('synthetic')
        export=self.root/'export'; export.mkdir()
        with self.assertRaises(b.Blocked): b.sqlite_candidate({'source':str(p),'source_identity':'fixture'},export,'run','postkamer',lambda:None)
    def test_symlink_tree_rejected(self):
        tree=self.root/'tree'; tree.mkdir(); (tree/'escape').symlink_to('/etc/hosts')
        with self.assertRaises(b.Blocked): b.tree_manifest(tree)
    def prepared(self):
        result={}
        for name in b.DATASETS:
            directory=self.root/'prepared'/name; directory.mkdir(parents=True)
            export=directory/'export'; export.mkdir()
            restore=directory/'restore'; restore.mkdir()
            metadata={'dataset':name,'method':'sqlite-online','table_counts':{'messages':1}}
            if name=='forgejo':
                payload=export/'payload'
                (payload/'data').mkdir(parents=True)
                fixture(payload/'data/forgejo.db')
                (payload/'custom/conf').mkdir(parents=True)
                (payload/'custom/conf/app.ini').write_text('APP_NAME = Synthetic fixture\n')
                (payload/'git/repositories').mkdir(parents=True)
                subprocess.run(['git','init','--bare',str(payload/'git/repositories/fixture.git')],capture_output=True,check=True)
                metadata['method']='sealed-tree'
            elif name=='recovery':
                payload=export/'payload'; payload.mkdir()
                (payload/'bootstrap.txt').write_text('Synthetic recovery fixture')
                inv={'components':{n:{'verified':True} for n in ['git-bundle','host-bootstrap','images','secrets-escrow','dataset-contracts']},'files':b.tree_manifest(payload)}
                b.atomic_json(payload/'recovery-inventory.json',inv)
                metadata['method']='sealed-tree'
            else:
                fixture(export/'database.sqlite')
            b.atomic_json(export/'manifest.json',metadata)
            result[name]={'export':export,'restore':restore,'manifest':b.tree_manifest(export)}
        return result
    def test_complete_bundle_receipt_readback(self):
        prepared=self.prepared(); repo=MemoryRepository(self.root/'repo')
        receipt=self.root/'receipt'; receipt.mkdir()
        result=b.verified_bundle(repo,prepared,receipt,'synthetic-run')
        self.assertEqual(set(result['candidates']),b.DATASETS)
        self.assertIn(('check','--read-data'),repo.calls)
        self.assertIn(('backup','receipt'),repo.calls)
        self.assertEqual(result['status'],'verified')
    def test_partial_bundle_cannot_publish_receipt(self):
        repo=MemoryRepository(self.root/'repo'); receipt=self.root/'receipt'; receipt.mkdir()
        with self.assertRaises(b.Blocked): b.verified_bundle(repo,{},receipt,'synthetic-run')
        self.assertEqual(repo.calls,[])
    def test_repository_corruption_no_receipt(self):
        prepared=self.prepared(); repo=MemoryRepository(self.root/'repo',fail_check=True)
        receipt=self.root/'receipt'; receipt.mkdir()
        with self.assertRaises(b.Blocked): b.verified_bundle(repo,prepared,receipt,'synthetic-run')
        self.assertNotIn(('backup','receipt'),repo.calls)
    def test_corrupt_restore_no_receipt(self):
        prepared=self.prepared(); repo=MemoryRepository(self.root/'repo',corrupt=True)
        receipt=self.root/'receipt'; receipt.mkdir()
        with self.assertRaises(b.Blocked): b.verified_bundle(repo,prepared,receipt,'synthetic-run')
        self.assertNotIn(('backup','receipt'),repo.calls)
    def test_receipt_mismatch_no_success(self):
        prepared=self.prepared(); repo=MemoryRepository(self.root/'repo',corrupt_receipt=True)
        receipt=self.root/'receipt'; receipt.mkdir()
        with self.assertRaises(b.Blocked): b.verified_bundle(repo,prepared,receipt,'synthetic-run')
    def test_disabled_status_never_green(self):
        with self.assertRaises(b.Blocked): b.freshness(config())
    def test_stale_or_partial_status_never_green(self):
        c=config(); c['enabled']=True; c['status_file']=str(self.root/'status.json')
        for content in [{'status':'failed','verified_at':100}, {'status':'verified','verified_at':100,'candidates':dict.fromkeys(b.DATASETS,'id'),'receipt_id':'r'}]:
            b.atomic_json(c['status_file'],content)
            with self.assertRaises(b.Blocked): b.freshness(c,now=200000)
    def test_k3s_inventory_not_assumed(self):
        export=self.root/'export'; export.mkdir()
        with self.assertRaises(b.Blocked): b.k3s_candidate(config()['contracts']['k3s'],export,'r',lambda:None)
    def test_forgejo_producer_not_assumed(self):
        export=self.root/'export'; export.mkdir()
        with self.assertRaises(b.Blocked): b.sealed_candidate(config()['contracts']['forgejo'],export,'r','forgejo',lambda:None)

class GuardTests(unittest.TestCase):
    def req(self,op='lease-acquire',run='a'*32,boot=None): return {'op':op,'run':run,'boot_id':boot}
    def session(self):
        self.now=10
        self.state={'host':'mau3','uuid':b.FS_UUID,'boot_id':'00000000-0000-0000-0000-000000000000','lock_count':0}
        return g.Session({'lease_seconds':20},probe=lambda c:dict(self.state),clock=lambda:self.now)
    def test_request_bounded_and_no_shell(self):
        for raw in [b'x'*4097,b'{}',json.dumps({'op':'poweroff-safe','run':'a'*32,'boot_id':None}).encode(),json.dumps({'op':'check','run':'a'*32,'boot_id':None,'path':'/etc/passwd'}).encode()]:
            with self.assertRaises(g.Rejected): g.request(raw)
    def health_fixture(self,uuid=b.FS_UUID,degraded='0',mounted=True,free=1024*1024*1024):
        mount={'filesystems':[{'target':'/backup','source':'/dev/md0','fstype':'ext4','uuid':uuid}]}
        def read(path,*args,**kwargs):
            name=str(path)
            if name.endswith('/degraded'): return degraded
            if name.endswith('/raid_disks'): return '2'
            if name.endswith('/array_state'): return 'clean'
            if name.endswith('/boot_id'): return '00000000-0000-0000-0000-000000000000'
            raise AssertionError('Unexpected read')
        with patch.object(g.socket,'gethostname',return_value='mau3'),patch.object(g.subprocess,'run',return_value=SimpleNamespace(returncode=0 if mounted else 1,stdout=json.dumps(mount).encode())),patch.object(g.Path,'read_text',read),patch.object(g.Path,'is_symlink',return_value=False),patch.object(g.Path,'exists',return_value=False),patch.object(g.Path,'iterdir',return_value=iter([])),patch.object(g.os,'stat',return_value=SimpleNamespace(st_dev=1)),patch.object(g.os,'statvfs',return_value=SimpleNamespace(f_bavail=free,f_frsize=1,f_favail=10000)):
            return g.health({'min_free_bytes':268435456})
    def test_mount_health_accepts_only_verified_target(self):
        self.assertEqual(self.health_fixture()['uuid'],b.FS_UUID)
    def test_mount_guard_failure_matrix(self):
        for overrides in [{'uuid':'wrong'},{'degraded':'1'},{'mounted':False},{'free':0}]:
            with self.subTest(**overrides),self.assertRaises(g.Rejected): self.health_fixture(**overrides)
    def test_malformed_operation_type_rejected(self):
        d=self.req(); d['op']={'unexpected':'object'}
        with self.assertRaises(g.Rejected): g.request(json.dumps(d).encode())
    def test_lease_owner(self):
        s=self.session(); s.handle(self.req())
        with self.assertRaises(g.Rejected): s.handle(self.req('lease-renew','b'*32))
    def test_expired_lease(self):
        s=self.session(); s.handle(self.req()); self.now=31
        with self.assertRaises(g.Rejected): s.handle(self.req('lease-renew'))
    def test_changed_boot(self):
        s=self.session(); s.handle(self.req()); self.state['boot_id']='11111111-1111-1111-1111-111111111111'
        with self.assertRaises(g.Rejected): s.handle(self.req('lease-renew'))
    def test_existing_repository_lock_refuses_acquire(self):
        s=self.session(); self.state['lock_count']=1
        with self.assertRaises(g.Rejected): s.handle(self.req())
    def test_own_restic_lock_does_not_break_renew(self):
        s=self.session(); s.handle(self.req()); self.state['lock_count']=1
        self.assertTrue(s.handle(self.req('lease-renew'))['ok'])
    def test_guard_probe_failure(self):
        s=self.session(); s.handle(self.req())
        def bad(c): raise g.Rejected('synthetic wrong mount')
        s.probe=bad
        with self.assertRaises(g.Rejected): s.handle(self.req('lease-renew'))
    def test_release(self):
        s=self.session(); s.handle(self.req()); s.handle(self.req('lease-release'))
        self.assertIsNone(s.owner)

class RecoveryTests(unittest.TestCase):
    def example(self): return json.loads((ROOT/'bootstrap/recovery/recovery-set.example.json').read_text())
    def test_design_is_not_ready(self): self.assertFalse(r.assess(self.example())['ready_for_isolated_test'])
    def test_structural_readiness_is_never_full_restore_proof(self):
        d=self.example()
        for v in d['components'].values(): v.update(independently_available=True,verified=True)
        d['server4']={'identity_confirmed':True,'isolated':True,'hostname':'synthetic-test-target','ip':'192.0.2.4'}
        d['artifacts']=[{'path':'synthetic-fixture','sha256':'0'*64}]
        result=r.assess(d)
        self.assertTrue(result['ready_for_isolated_test'])
        self.assertFalse(result['full_disaster_recovery_proven'])
    def test_inline_password_refused(self):
        d=self.example(); d['password']='synthetic-not-a-secret'
        with self.assertRaises(ValueError): r.assess(d)
    def test_artifact_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): r.verify_artifacts({'artifacts':[{'path':'../escape','sha256':'0'*64}]},t)
    def test_server4_must_not_be_production(self):
        d=self.example(); d['server4']={'identity_confirmed':True,'isolated':True,'ip':'192.168.0.162','hostname':'mau2'}
        with self.assertRaises(ValueError): r.assess(d)
    def test_checksum_detects_tampering(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fixture'; p.write_bytes(b'synthetic')
            d={'artifacts':[{'path':'fixture','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]}
            self.assertEqual(r.verify_artifacts(d,t),1)
            p.write_bytes(b'changed')
            with self.assertRaises(ValueError): r.verify_artifacts(d,t)

if __name__=='__main__': unittest.main()
