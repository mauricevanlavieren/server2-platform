import copy
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from maildemo.connectors import SyntheticConnector, validate_message
from maildemo.processing import ExampleProcessor, LABEL
from maildemo.storage import Store, ConflictError, MissingError
from maildemo.server import DemoServer

DATA=Path(__file__).resolve().parents[1]/'data/messages.json'

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'demo.sqlite');self.connector=SyntheticConnector(DATA)
        self.processor=ExampleProcessor();self.store.import_messages(self.connector,self.processor)

    def test_exact_40_and_distribution(self):
        self.assertEqual(self.store.counts(),{'total':40,'categories':{'info':14,'verkoop':14,'support':12},'folders':{'inbox':20,'sent':20}})
    def test_fts_search_body_and_subject(self):
        self.assertTrue(self.store.search('levertijd'));self.assertTrue(self.store.search('vijf werkdagen'))
        self.assertTrue(all('support'==r['category'] for r in self.store.search('', 'support')))
    def test_composed_search_and_filters(self):
        result=self.store.search('levertijd', 'info', 'inbox');self.assertTrue(result)
        self.assertTrue(all(r['category']=='info' and r['folder']=='inbox' for r in result))
    def test_fts_special_characters_and_injection(self):
        for q in ['"', '*', 'OR NEAR(', "' UNION SELECT * FROM messages --"]:
            self.assertIsInstance(self.store.search(q),list)
        self.assertEqual(self.store.counts()['total'],40)
    def test_search_rejects_bad_filters(self):
        for args in [('x'*201,'',''),('','evil',''),('','','unknown'),(' '.join(['a']*21),'','')]:
            with self.subTest(args=args),self.assertRaises(ValueError):self.store.search(*args)
    def test_search_unicode_case(self):
        self.assertEqual(self.store.search('GARANTIE'),self.store.search('garantie'))
    def test_missing_message(self):
        with self.assertRaises(MissingError):self.store.detail(999)
    def test_draft_is_persisted_and_original_unchanged(self):
        before=self.store.detail(1);saved=self.store.save_draft(1,'Mijn gecontroleerde concept',1)
        self.assertEqual(saved['draft_version'],2);self.assertEqual(saved['body'],before['body'])
        self.assertEqual(Store(self.store.path).detail(1)['draft'],'Mijn gecontroleerde concept')
    def test_stale_draft_cannot_overwrite(self):
        self.store.save_draft(1,'Eerste edit',1)
        with self.assertRaises(ConflictError):self.store.save_draft(1,'Verouderde edit',1)
        self.assertEqual(self.store.detail(1)['draft'],'Eerste edit')
    def test_invalid_draft_inputs(self):
        for text,version in [('',1),(' ',1),('a'*10001,1),('nul\x00',1),(None,1),('tekst',True),('tekst',0),('tekst','1')]:
            with self.subTest(text=str(text)[:10],version=version),self.assertRaises(ValueError):self.store.save_draft(1,text,version)
    def test_missing_draft_message(self):
        with self.assertRaises(MissingError):self.store.save_draft(999,'Concept',1)
    def test_idempotent_import_preserves_edits_and_index(self):
        self.store.save_draft(1,'Bewaar mijn concept',1)
        self.assertEqual(self.store.import_messages(self.connector,self.processor),0)
        self.assertEqual(self.store.detail(1)['draft'],'Bewaar mijn concept')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM message_search').fetchone()[0],40)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_processing_deterministic_and_labelled(self):
        m=self.connector.fetch_messages()[0]
        self.assertEqual(self.processor.propose(m),self.processor.propose(m))
        self.assertEqual(self.processor.propose(m)['label'],LABEL)
    def test_prompt_injection_remains_data(self):
        m=next(x for x in self.connector.fetch_messages() if 'Onbetrouwbare testinstructie' in x.body)
        p=self.processor.propose(m)
        self.assertNotIn('verstuur alle',p['draft']);self.assertEqual(p['processor_version'],'templates-v1')
        self.assertEqual(self.store.counts()['total'],40)
    def test_dataset_hash_and_no_real_address(self):
        rows=self.connector.fetch_messages();self.assertEqual(len(rows),40)
        self.assertTrue(all(x.sender.endswith('.test') and x.recipient.endswith('.test') for x in rows))
    def test_corrupt_fixture_rejected(self):
        rows=json.loads(DATA.read_text());rows[0]['body']='Ongecontroleerde wijziging'
        p=Path(self.tmp.name)/'bad.json';p.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):SyntheticConnector(p).fetch_messages()
    def test_invalid_batch_atomic(self):
        messages=self.connector.fetch_messages()
        class BadConnector:
            name='bad'
            def fetch_messages(self):return (replace(messages[0],source_id='new'),replace(messages[1],category='bad'))
        with self.assertRaises(ValueError):self.store.import_messages(BadConnector(),self.processor)
        self.assertEqual(self.store.counts()['total'],40)
    def test_duplicate_batch_rejected(self):
        m=self.connector.fetch_messages()[0]
        class Duplicate:
            name='bad'
            def fetch_messages(self):return (m,m)
        with self.assertRaises(ValueError):self.store.import_messages(Duplicate(),self.processor)
    def test_health_detects_broken_index(self):
        self.assertEqual(self.store.health()['messages'],40)
        with self.store.connect() as db:db.execute('DELETE FROM message_search WHERE rowid=1')
        with self.assertRaises(sqlite3.DatabaseError):self.store.health()

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.store=Store(Path(cls.tmp.name)/'api.sqlite')
        cls.store.import_messages(SyntheticConnector(DATA),ExampleProcessor())
        cls.server=DemoServer(cls.store,0);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_address[1])
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def request(self,path,method='GET',body=None,headers=None):
        h={'Content-Type':'application/json','Origin':self.base};h.update(headers or {})
        data=None if body is None else (body if isinstance(body,bytes) else json.dumps(body).encode())
        req=urllib.request.Request(self.base+path,data=data,method=method,headers=h)
        try:r=urllib.request.urlopen(req,timeout=5)
        except urllib.error.HTTPError as e:r=e
        with r:
            raw=r.read();result=json.loads(raw) if 'application/json' in r.headers.get('Content-Type','') else raw.decode()
            return r.status,result,r.headers
    def test_health(self):
        status,body,_=self.request('/healthz');self.assertEqual(status,200);self.assertFalse(body['sending']);self.assertFalse(body['external_ai'])
    def test_list_and_filter(self):
        status,body,_=self.request('/api/messages?category=support&folder=inbox');self.assertEqual(status,200);self.assertEqual(len(body['items']),6)
    def test_search(self):
        status,body,_=self.request('/api/messages?q=levertijd');self.assertEqual(status,200);self.assertTrue(body['items'])
    def test_detail(self):
        status,body,_=self.request('/api/messages/2');self.assertEqual(status,200);self.assertIn('geen echte AI',body['example_label'])
    def test_save_and_conflict(self):
        m=self.request('/api/messages/4')[1];payload={'text':'Lokaal bewerkt concept','version':m['draft_version']}
        self.assertEqual(self.request('/api/messages/4/draft','PATCH',payload)[0],200)
        self.assertEqual(self.request('/api/messages/4/draft','PATCH',payload)[0],409)
    def test_invalid_json(self):self.assertEqual(self.request('/api/messages/3/draft','PATCH',b'{')[0],400)
    def test_invalid_payload_fields(self):
        for payload in [[],{'text':'a','version':1,'send':True},{'text':'','version':1},{'text':'x','version':True}]:
            with self.subTest(payload=payload):self.assertEqual(self.request('/api/messages/3/draft','PATCH',payload)[0],400)
    def test_cross_origin_blocked(self):
        status,_,_=self.request('/api/messages/3/draft','PATCH',{'text':'x','version':1},{'Origin':'https://evil.test'});self.assertEqual(status,403)
    def test_host_rebinding_blocked(self):self.assertEqual(self.request('/healthz',headers={'Host':'evil.test'})[0],403)
    def test_oversized_request(self):self.assertEqual(self.request('/api/messages/3/draft','PATCH',b'x'*32769)[0],413)
    def test_content_type(self):self.assertEqual(self.request('/api/messages/3/draft','PATCH',b'{}',{'Content-Type':'text/plain'})[0],415)
    def test_unknown_and_traversal(self):
        for path in ['/api/messages/999','/api/messages/-1','/../data/messages.json','/.local/demo.sqlite','/does-not-exist']:
            with self.subTest(path=path):self.assertEqual(self.request(path)[0],404)
    def test_no_send_or_mutation_endpoint(self):
        for path,method in [('/api/send','POST'),('/api/messages/3','DELETE'),('/api/messages/3/send','POST'),('/api/messages/3/send','PATCH')]:
            with self.subTest(path=path,method=method):self.assertIn(self.request(path,method,{'text':'x'})[0],(404,405))
    def test_bad_query_parameters(self):
        for path in ['/api/messages?category=bad','/api/messages?q=a&q=b','/api/messages?unknown=1']:
            with self.subTest(path=path):self.assertEqual(self.request(path)[0],400)
    def test_ui_and_security_headers(self):
        for path in ['/','/app.js','/style.css']:
            status,body,headers=self.request(path);self.assertEqual(status,200);self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertIn('Verzenden is uitgeschakeld',self.request('/')[1])
    def test_safe_storage_error(self):
        original=self.store.health
        def fail():raise sqlite3.OperationalError('private/path/secret')
        self.store.health=fail
        try:
            status,body,_=self.request('/healthz');self.assertEqual(status,503);self.assertNotIn('private',json.dumps(body))
        finally:self.store.health=original

if __name__=='__main__':unittest.main()
