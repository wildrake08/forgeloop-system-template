import json,subprocess,sys,tempfile,unittest
from pathlib import Path

class CliTest(unittest.TestCase):
    def run_cli(self,*args,check=True):return subprocess.run([sys.executable,'-m','clses_mvas_v1.cli',*args],capture_output=True,text=True,check=check)
    def test_help(self):self.assertIn('clses-v1',self.run_cli('--help').stdout)
    def test_init_and_driver_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            init=json.loads(self.run_cli('--root',folder,'init','--system-id','cli-system').stdout);self.assertEqual(init['mode'],'strict');driver=json.loads(self.run_cli('--root',folder,'driver-register','--name','codex','--kind','codex').stdout);self.assertEqual(driver['kind'],'codex')
    def test_invalid_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            self.run_cli('--root',folder,'init');cp=self.run_cli('--root',folder,'execute','--work-id','missing',check=False);self.assertNotEqual(cp.returncode,0);self.assertIn('error',json.loads(cp.stderr))
if __name__=='__main__':unittest.main()
