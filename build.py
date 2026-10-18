"""Release preflight with generator and independently implemented verifier."""
import json,subprocess,sys
from pathlib import Path
from clses_mvas_v1.release_assessment import generate
if __name__=='__main__':
    result=generate();root=Path(__file__).resolve().parent;independent=subprocess.run([sys.executable,str(root/'independent_verify.py'),str(root/'verification/RELEASE_ASSESSMENT_4.6.1.json'),'--root',str(root)]);print(json.dumps(result,indent=2));raise SystemExit(0 if result['valid'] and independent.returncode==0 else 1)
