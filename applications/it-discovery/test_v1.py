import unittest,tempfile,os,sys,json,threading,http.client
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));TMP=tempfile.TemporaryDirectory();os.environ['DISCOVERY_DB']=str(Path(TMP.name)/'v1.sqlite')
import app,features
from http.server import ThreadingHTTPServer
class V1Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):app.init();features.setup(app)
 def project(self):return dict(customer='Fictief MKB',synthetic=True,consent='Fictieve scopetoestemming',approved_by='Demo operator: akkoord',execution_plan='Handmatige demo',rollback_plan='Demo terugzetten',steps=['Afgerond']*14)
 def test_complete_persistent_workflow(self):
  id=features.save_project(self.project());p=next(p for p in features.projects() if p['id']==id);self.assertEqual(p['steps'],['Afgerond']*14);p.pop('updated');p['steps'][-1]='Bezig';features.save_project(p);self.assertEqual(next(p for p in features.projects() if p['id']==id)['steps'][-1],'Bezig')
 def test_no_approval_bypass(self):
  p=self.project();p['approved_by']=''
  with self.assertRaises(ValueError):features.save_project(p)
 def test_consent_and_rollback_required(self):
  for field in ('consent','rollback_plan'):
   p=self.project();p[field]=''
   with self.assertRaises(ValueError):features.save_project(p)
 def test_real_data_flag_rejected(self):
  p=self.project();p['synthetic']=False
  with self.assertRaises(ValueError):features.save_project(p)
 def test_alert_debounce_and_recovery(self):
  for i in range(2):features.evaluate({'simulation':(True,'Synthetic disk alert')},100+i)
  self.assertFalse(next(a for a in features.monitor()['alerts'] if a['id']=='simulation')['active']);features.evaluate({'simulation':(True,'Synthetic disk alert')},102);self.assertTrue(next(a for a in features.monitor()['alerts'] if a['id']=='simulation')['active'])
  for i in range(2):features.evaluate({'simulation':(False,'Recovered')},103+i)
  self.assertFalse(next(a for a in features.monitor()['alerts'] if a['id']=='simulation')['active'])
 def test_reports_separate_evidence(self):
  for kind in features.KINDS:
   r=features.report('demo',kind);self.assertIn('Vastgestelde feiten',r);self.assertIn('Afgeleide conclusies',r);self.assertIn('Aannames',r);self.assertIn('Nog te verifiëren',r)
  self.assertNotIn('<script>',features.print_html('<script>alert(1)</script>'))
 def test_http_project_and_health(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),features.handler(app.Handler));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   c=http.client.HTTPConnection(*server.server_address);c.request('POST','/api/projects',body=json.dumps(self.project()),headers={'Host':'127.0.0.1:8780','Origin':'http://127.0.0.1:8780','Content-Type':'application/json'});r=c.getresponse();self.assertEqual(r.status,200);r.read();c.close()
   c=http.client.HTTPConnection(*server.server_address);c.request('GET','/healthz',headers={'Host':'127.0.0.1:8780'});r=c.getresponse();self.assertEqual(r.status,200);r.read();c.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
