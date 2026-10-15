"""Regression tests of the actual frontend controller, without packages."""
from pathlib import Path
import shutil
import subprocess
import unittest

class UiControllerTests(unittest.TestCase):
    def test_browser_controller_regressions(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'UI-regressietests vereisen de bestaande Node.js-runtime; geen npm-packages.')
        result = subprocess.run([node, str(Path(__file__).with_name('ui_regression.cjs'))],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
        self.assertIn('"cases":9', result.stdout)
        print('\n'+result.stdout)
