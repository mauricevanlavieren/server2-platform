import copy
import unittest
from tools.security_gate import assess

class SecurityGateTests(unittest.TestCase):
    def report(self,vulns):return {'Metadata':{'OS':{'Family':'debian'}},'Results':[{'Class':'os-pkgs','Packages':[{'Name':'example'}],'Vulnerabilities':vulns}]}
    def test_clean_inventory(self):self.assertEqual(assess(self.report([])),[])
    def test_high_without_fix_blocks(self):self.assertEqual(len(assess(self.report([{'Severity':'HIGH'}]))),1)
    def test_critical_blocks(self):self.assertEqual(len(assess(self.report([{'Severity':'CRITICAL'}]))),1)
    def test_unknown_blocks(self):self.assertEqual(len(assess(self.report([{'Severity':'UNKNOWN'}]))),1)
    def test_missing_severity_blocks(self):self.assertEqual(len(assess(self.report([{}]))),1)
    def test_missing_scan_fails(self):
        for r in [{},{'Results':[]},self.report([])|{'Metadata':{}}]:
            with self.subTest(r=r),self.assertRaises(ValueError):assess(r)
    def test_missing_inventory_fails(self):
        r=self.report([]);r['Results'][0]['Packages']=[]
        with self.assertRaises(ValueError):assess(r)
