import json,subprocess,sys,tempfile,unittest
from pathlib import Path

class IntakeCliTest(unittest.TestCase):
    def test_help(self):
        cp=subprocess.run([sys.executable,'-m','clses_mvas_v1.intake','--help'],capture_output=True,text=True);self.assertEqual(cp.returncode,0);self.assertIn('clses-intake',cp.stdout)
    def test_start_persists_state_and_returns_questions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';cp=subprocess.run([sys.executable,'-m','clses_mvas_v1.intake','start','--profile','point-of-sale','--output',str(path)],capture_output=True,text=True);self.assertEqual(cp.returncode,0);self.assertTrue(path.exists());self.assertEqual(json.loads(cp.stdout)['question_count'],5)
    def test_status_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json';subprocess.run([sys.executable,'-m','clses_mvas_v1.intake','start','--profile','point-of-sale','--output',str(path)],check=True,capture_output=True,text=True);before=path.read_bytes();cp=subprocess.run([sys.executable,'-m','clses_mvas_v1.intake','status',str(path)],capture_output=True,text=True);self.assertEqual(cp.returncode,0);self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
