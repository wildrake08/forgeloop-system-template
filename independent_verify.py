"""Independent release verifier: no use of the assessment generator's verification code."""
from __future__ import annotations
import argparse,base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from clses_mvas_v1.validator import assess

LOCAL_TOP_LEVEL={'.venv','venv','.direnv','.pytest_cache','.mypy_cache','.ruff_cache','htmlcov','build','dist'}
LOCAL_FILES={'.coverage','.DS_Store'}

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value):return hashlib.sha256(value if isinstance(value,bytes) else canonical(value)).hexdigest()
def inventory(root):
    root=Path(root);items=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        top=relative.parts[0] if relative.parts else ''
        if (not path.is_file() or path.is_symlink() or '__pycache__' in relative.parts or path.suffix=='.pyc' or top in ('.git','.clses-v1') or top in LOCAL_TOP_LEVEL or top.endswith('.egg-info') or str(relative) in LOCAL_FILES or str(relative) in ('.clses-template/template-manifest.json','verification/RELEASE_ASSESSMENT_4.6.2.json')):continue
        items.append({'path':str(relative),'sha256':digest(path.read_bytes()),'size':path.stat().st_size})
    return sorted(items,key=lambda item:item['path'])
def signature_valid(bundle):
    try:
        if bundle['signer']['algorithm']!='RSA-SHA256':return False
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);public=root/'public.pem';data=root/'data';signature=root/'signature';public.write_text(bundle['signer']['public_key_pem']);data.write_bytes(canonical(bundle['evidence']));signature.write_bytes(base64.b64decode(bundle['signer']['signature_base64'],validate=True));return subprocess.run(['openssl','dgst','-sha256','-verify',str(public),'-signature',str(signature),str(data)],capture_output=True).returncode==0
    except (KeyError,ValueError,subprocess.SubprocessError):return False
def verify(path,root):
    root=Path(root);bundle=json.loads(Path(path).read_text());e=bundle.get('evidence',{});policy=json.loads((root/'verification/ASSESSMENT_POLICY_4.6.2.json').read_text());parts=e.get('parts',{});dimensions=e.get('dimensions',{});current=inventory(root);stored=e.get('inventory',[]);stored_paths={item.get('path') for item in stored};part_files=all(all(any(path==wanted or path.startswith(wanted.rstrip('/')+'/') for path in stored_paths) for wanted in part.get('files',[])) for part in parts.values());manifest=assess(e.get('manifest',{}));checks={'signature_valid':signature_valid(bundle),'evidence_digest':bundle.get('evidence_sha256')==digest(e),'policy_digest':e.get('policy_sha256')==digest(policy),'assessment_format':e.get('format')==policy.get('assessment_format'),'version':e.get('version')==policy.get('version'),'exact_parts':set(parts)==set(policy.get('required_parts',[])),'exact_dimensions':set(dimensions)==set(policy.get('required_dimensions',[])),'all_dimensions_true':all(dimensions.get(name) is True for name in policy.get('required_dimensions',[])),'part_files_bound':part_files,'part_verdicts':all(part.get('intrinsic')=='conformant' and part.get('relational')=='adequate_for_declared_part_conditions' and part.get('evidence',{}).get('pass') is True for part in parts.values()),'minimum_tests':e.get('tests',{}).get('pass') is True and e.get('tests',{}).get('tests',0)>=policy.get('minimum_tests',10**9),'inventory_internal':e.get('inventory_sha256')==digest(stored),'inventory_current':e.get('inventory_sha256')==digest(current),'manifest_digest':e.get('manifest_sha256')==digest(e.get('manifest',{})),'manifest_artifact_level':manifest.get('artifact_level')=='pass','manifest_system_level':manifest.get('system_level')=='pass','whole_intrinsic':e.get('whole',{}).get('intrinsic')=='conformant' and e.get('whole',{}).get('parts_complete') is True,'whole_relational':e.get('whole',{}).get('relational')=='purpose_sustaining_general_assurance_framework_adequate' and e.get('whole',{}).get('live_cycle_valid') is True,'claim_boundary':all(term in e.get('claim_boundary','') for term in policy.get('required_claim_boundary_terms',[]))};return {'valid':all(checks.values()),'checks':checks,'parts':len(parts),'tests':e.get('tests',{}).get('tests',0)}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('assessment');parser.add_argument('--root',default='.');args=parser.parse_args();result=verify(args.assessment,args.root);print(json.dumps(result,indent=2));return 0 if result['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
