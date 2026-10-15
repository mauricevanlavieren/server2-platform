import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
from maildemo.config import load_config
from maildemo.connectors import SyntheticConnector
from maildemo.processing import ExampleProcessor
from maildemo.storage import Store
from maildemo.server import DemoServer
from maildemo.healthcheck import main as healthcheck

class ContainerConfigTests(unittest.TestCase):
    def test_local_defaults(self):
        c=load_config({});self.assertEqual(c.bind,'127.0.0.1');self.assertEqual(c.port,8765);self.assertEqual(str(c.db),'.local/demo.sqlite')
    def test_container_configuration(self):
        c=load_config({'POSTKAMER_BIND':'0.0.0.0','POSTKAMER_PORT':'8766','POSTKAMER_DB':'/data/demo.sqlite'});self.assertEqual(c.bind,'0.0.0.0');self.assertIn('127.0.0.1:8766',c.allowed_hosts)
    def test_reject_unknown_binding(self):
        for bind in ['::','192.0.2.123','example.test','']:
            with self.subTest(bind=bind),self.assertRaises(ValueError):load_config({'POSTKAMER_BIND':bind})
    def test_reject_invalid_ports(self):
        for port in ['0','80','65536','x','8765.0']:
            with self.subTest(port=port),self.assertRaises(ValueError):load_config({'POSTKAMER_PORT':port})
    def test_reject_empty_db(self):
        for db in ['', ' ', '\x00']:
            with self.subTest(db=db),self.assertRaises(ValueError):load_config({'POSTKAMER_DB':db})
    def test_reject_host_wildcards_and_remote_origins(self):
        for hosts in ['*','evil.test:8765','127.0.0.1:80','localhost:65536','localhost:8765,','http://localhost:8765']:
            with self.subTest(hosts=hosts),self.assertRaises(ValueError):load_config({'POSTKAMER_ALLOWED_HOSTS':hosts})
    def test_explicit_local_forward_authority(self):
        self.assertEqual(load_config({'POSTKAMER_ALLOWED_HOSTS':'localhost:8766,127.0.0.1:8765'}).allowed_hosts,('localhost:8766','127.0.0.1:8765'))
    def test_healthcheck_invalid_config_fails_closed(self):
        with patch.dict(os.environ,{'POSTKAMER_PORT':'invalid'},clear=True):self.assertEqual(healthcheck(),1)
    def test_healthcheck_unreachable_fails_closed(self):
        with patch('maildemo.healthcheck.urllib.request.build_opener',side_effect=OSError('offline')):self.assertEqual(healthcheck(),1)
    def test_healthcheck_actual_service_and_origin(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'db.sqlite');store.import_messages(SyntheticConnector(Path(__file__).resolve().parents[1]/'data/messages.json'),ExampleProcessor())
            server=DemoServer(store,0,bind='0.0.0.0');thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                port=server.server_address[1]
                with patch.dict(os.environ,{'POSTKAMER_PORT':str(port)},clear=True):self.assertEqual(healthcheck(),0)
                request=urllib.request.Request(f'http://127.0.0.1:{port}/api/messages/1/draft',data=json.dumps({'text':'container-test','version':1}).encode(),method='PATCH',headers={'Content-Type':'application/json','Origin':'http://evil.test'})
                with self.assertRaises(urllib.error.HTTPError) as result:urllib.request.urlopen(request)
                self.assertEqual(result.exception.code,403)
            finally:server.shutdown();server.server_close();thread.join()
    def test_healthcheck_rejects_wrong_data_or_capabilities(self):
        from io import BytesIO
        for body in [{'status':'ok','messages':39,'fts5':True,'sending':False,'external_ai':False},{'status':'ok','messages':40,'fts5':True,'sending':True,'external_ai':False},{'status':'ok','messages':40,'fts5':False,'sending':False,'external_ai':False}]:
            with self.subTest(body=body),patch('maildemo.healthcheck.urllib.request.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value=BytesIO(json.dumps(body).encode());self.assertEqual(healthcheck(),1)
