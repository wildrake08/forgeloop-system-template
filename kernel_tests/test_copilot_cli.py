import json,subprocess,sys,tempfile,unittest
from clses_mvas_v1.engine import Engine

class CopilotCliTest(unittest.TestCase):
    def run_cli(self,*args,check=True):return subprocess.run([sys.executable,'-m','clses_mvas_v1.copilot_cli',*args],capture_output=True,text=True,check=check)
    def test_help(self):self.assertIn('clses-copilot',self.run_cli('--help').stdout)
    def test_status(self):
        with tempfile.TemporaryDirectory() as folder:
            Engine(folder).init();result=json.loads(self.run_cli('--root',folder,'status').stdout);self.assertEqual(result['stage'],'initialized');self.assertIn('conversation never',result['authority_rule'])
    def test_uninitialized_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            cp=self.run_cli('--root',folder,'status',check=False);self.assertNotEqual(cp.returncode,0);self.assertIn('error',json.loads(cp.stderr))
if __name__=='__main__':unittest.main()
