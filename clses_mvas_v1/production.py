"""Fail-closed assessment of externally grounded production evidence."""
from __future__ import annotations
import argparse,base64,json,operator,subprocess,tempfile,time
from pathlib import Path
from .store import canonical,digest

OPS={'>=':operator.ge,'>':operator.gt,'<=':operator.le,'<':operator.lt,'==':operator.eq,'!=':operator.ne}
MONITORS={'source','dependencies','infrastructure','runtime','security','regulatory'}
TOP={'format','system_id','spec_digest','assessed_at','artifact','acceptance','deployment','observations','change_monitors','supply_chain','recovery','operations','closure'}

def inventory(root):
    root=Path(root);return [{'path':str(path.relative_to(root)),'sha256':digest(path.read_bytes()),'size':path.stat().st_size} for path in sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink())]

def signature_valid(bundle,public_key):
    try:
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data=root/'evidence';sig=root/'signature';data.write_bytes(canonical(bundle['evidence']));sig.write_bytes(base64.b64decode(bundle['signature_base64'],validate=True));return subprocess.run(['openssl','dgst','-sha256','-verify',str(public_key),'-signature',str(sig),str(data)],capture_output=True).returncode==0
    except (KeyError,ValueError,subprocess.SubprocessError):return False

def assess(bundle,spec,deployment_root,trusted_public_key,now=None):
    now=int(time.time()) if now is None else int(now);errors=[];checks={};e=bundle.get('evidence',{});spec=json.loads(Path(spec).read_text()) if isinstance(spec,(str,Path)) else spec
    checks['external_signature']=signature_valid(bundle,trusted_public_key);checks['evidence_digest']=bundle.get('evidence_sha256')==digest(e);checks['exact_shape']=set(e)==TOP;checks['format']=e.get('format')=='CLSES-production-evidence/v1';checks['assessment_time']=isinstance(e.get('assessed_at'),int) and e['assessed_at']<=now;checks['identity']=e.get('system_id')==spec.get('system_id') and e.get('spec_digest')==digest(spec)
    if not all((checks['exact_shape'],checks['format'],checks['identity'])):errors.append('production evidence shape, format, or specification identity is invalid')
    declared=set(spec.get('components',[]));artifact=e.get('artifact',{});entries=artifact.get('entries',[]);artifact_paths={'src/'+x.get('path','') for x in entries};checks['declared_components_exact']=declared==artifact_paths;checks['artifact_digest']=artifact.get('digest')==digest(entries)
    current=inventory(deployment_root);deployment=e.get('deployment',{});checks['deployment_current']=deployment.get('artifact_digest')==artifact.get('digest') and deployment.get('current_inventory')==current and current==entries
    criteria={item['key']:item for item in spec.get('requirements',[])+spec.get('outcomes',[])};observations=e.get('observations',[]);observed={}
    for item in observations:
        key=item.get('criterion_key')
        if key in observed:errors.append('duplicate observation for '+str(key));continue
        observed[key]=item;criterion=criteria.get(key)
        if not criterion:errors.append('observation has unknown criterion '+str(key));continue
        valid=(item.get('measurement_key')==criterion['measurement_key'] and item.get('unit')==criterion['unit'] and isinstance(item.get('value'),(int,float)) and OPS[criterion['op']](item['value'],criterion['threshold']) and item.get('coverage')==1.0 and item.get('source')==criterion['source'] and isinstance(item.get('method'),str) and bool(item['method']) and isinstance(item.get('adapter_digest'),str) and len(item['adapter_digest'])==64 and isinstance(item.get('raw_evidence_sha256'),str) and len(item['raw_evidence_sha256'])==64 and isinstance(item.get('observed_at'),int) and isinstance(item.get('expires_at'),int) and item['observed_at']<=now<=item['expires_at'] and item.get('environment_id')==deployment.get('environment_id'))
        if not valid:errors.append('criterion evidence is invalid, failing, stale, or ungrounded: '+str(key))
    checks['criteria_exact']=set(observed)==set(criteria);checks['criteria_grounded']=checks['criteria_exact'] and not any(x.startswith('criterion evidence') or x.startswith('duplicate observation') or x.startswith('observation has unknown') for x in errors)
    acceptance=e.get('acceptance',{});checks['acceptance']=acceptance.get('artifact_digest')==artifact.get('digest') and acceptance.get('passed') is True and all(isinstance(acceptance.get(k),str) and acceptance[k] for k in ('actor','decision_digest','evidence_digest'))
    monitors=e.get('change_monitors',[]);indexed={x.get('domain'):x for x in monitors};checks['change_monitors']=set(indexed)==MONITORS and len(monitors)==len(MONITORS) and all(x.get('status')=='current' and x.get('checked_at',now+1)<=now<=x.get('expires_at',-1) and isinstance(x.get('evidence_digest'),str) and len(x['evidence_digest'])==64 for x in monitors)
    supply=e.get('supply_chain',{});checks['supply_chain']=all(isinstance(supply.get(k),str) and len(supply[k])==64 for k in ('sbom_digest','provenance_digest','dependency_lock_digest','vulnerability_scan_digest','license_scan_digest')) and supply.get('critical_vulnerabilities')==0 and supply.get('policy_passed') is True
    recovery=e.get('recovery',{});checks['recovery']=recovery.get('rollback_tested') is True and recovery.get('restore_tested') is True and all(isinstance(recovery.get(k),str) and len(recovery[k])==64 for k in ('rollback_evidence_digest','restore_evidence_digest'))
    operations=e.get('operations',{});checks['operations']=operations.get('monitoring_active') is True and operations.get('open_critical_incidents')==0 and operations.get('observed_from',now+1)<=operations.get('observed_until',-1)<=now and isinstance(operations.get('telemetry_digest'),str) and len(operations['telemetry_digest'])==64
    closure=e.get('closure',{});checks['closure']=closure.get('decision')=='closed_verified' and closure.get('artifact_digest')==artifact.get('digest') and closure.get('spec_digest')==digest(spec) and all(isinstance(closure.get(k),str) and closure[k] for k in ('actor','decision_digest'))
    checks['deployment_authorized']=all(isinstance(deployment.get(k),str) and deployment[k] for k in ('environment_id','deployment_digest','authorization_digest')) and deployment.get('deployed_at',now+1)<=now
    for name,value in checks.items():
        if not value:errors.append('failed production check: '+name)
    valid=not errors
    return {'valid':valid,'checks':checks,'errors':sorted(set(errors)),'intrinsic':'conformant' if valid else 'nonconformant','relational':'adequate_for_declared_production_conditions' if valid else 'not_adequate','claim_boundary':{'system_id':e.get('system_id'),'environment_id':deployment.get('environment_id'),'assessed_at':e.get('assessed_at'),'evidence_expires_at':min([x.get('expires_at',0) for x in observations+monitors],default=0)}}

def main():
    parser=argparse.ArgumentParser(prog='clses-production-verify');parser.add_argument('bundle');parser.add_argument('--spec',required=True);parser.add_argument('--deployment-root',required=True);parser.add_argument('--trusted-public-key',required=True);args=parser.parse_args();result=assess(json.loads(Path(args.bundle).read_text()),args.spec,args.deployment_root,args.trusted_public_key);print(json.dumps(result,indent=2));return 0 if result['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
