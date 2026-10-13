import unittest,tempfile,os,sys,json
from pathlib import Path
TMP=tempfile.TemporaryDirectory();os.environ['DISCOVERY_DB']=str(Path(TMP.name)/'test.sqlite');sys.path.insert(0,str(Path(__file__).parent));import app
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):app.init()
 def test_synthetic_seed(self):self.assertEqual(len(app.state('demo')['assets']),6)
 def test_live_separated(self):self.assertEqual(app.state('live')['assets'],[])
 def test_invalid_dataset(self):
  with self.assertRaises(ValueError):app.state('../secrets')
 def test_provider_is_demo(self):self.assertIn('geen echte AI',app.DemoAdvisor().analyze(app.state('demo'))['mode'])
 def test_reports(self):
  for kind in ['technical','management','risk','installation','maintenance','advice']:self.assertIn('menselijke goedkeuring',app.report('demo',kind))
 def test_no_execution(self):self.assertFalse(app.state('demo')['execution_enabled'])
 def test_no_external_ai(self):self.assertFalse(app.state('demo')['external_ai'])
 def test_metric_units(self):
  self.assertEqual(app.quantity('1','cpu'),1000)
  self.assertEqual(app.quantity('250m','cpu'),250)
  self.assertEqual(app.quantity('1048576','memory'),1)
  self.assertEqual(app.quantity('1Gi','memory'),1024)
  with self.assertRaises(ValueError):app.quantity('unknown','cpu')
 def test_unknown_relationship(self):self.assertTrue(any(not e['confirmed'] for e in app.state('demo')['edges']))
if __name__=='__main__':unittest.main(verbosity=2)
