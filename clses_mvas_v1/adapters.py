"""Vendor-neutral evidence-adapter protocol with strict process boundaries."""
from __future__ import annotations
import json,os,subprocess,tempfile,time
from pathlib import Path
from .store import canonical,digest

MANIFEST_KEYS={'format','id','version','digest','capabilities','trust_anchor','execution_boundary','command','timeout_seconds'}
REQUEST_KEYS={'format','request_id','system_id','environment_id','control_id','artifact_id','evidence_type','inputs','deadline'}
RESULT_KEYS={'format','request_id','adapter_id','adapter_digest','evidence_type','passed','measurements','raw_evidence_sha256','observed_at','expires_at'}

def validate_manifest(value):
    if not isinstance(value,dict) or set(value)!=MANIFEST_KEYS or value.get('format')!='CLSES-adapter-manifest/v1' or not value.get('id') or not value.get('capabilities') or not isinstance(value.get('command'),list) or not value['command'] or value.get('execution_boundary') not in ('isolated','external_service','read_only') or not 0<value.get('timeout_seconds',0)<=3600:raise ValueError('invalid adapter manifest')
    core={k:value[k] for k in MANIFEST_KEYS-{'digest'}}
    if value.get('digest')!=digest(core):raise ValueError('adapter manifest digest mismatch')
    return value

def validate_request(value,now=None):
    now=int(time.time()) if now is None else now
    if not isinstance(value,dict) or set(value)!=REQUEST_KEYS or value.get('format')!='CLSES-adapter-request/v1' or not all(value.get(k) for k in ('request_id','system_id','environment_id','control_id','artifact_id','evidence_type')) or not isinstance(value.get('inputs'),dict) or value.get('deadline',0)<now:raise ValueError('invalid or expired adapter request')
    return value

def validate_result(value,manifest,request,now=None):
    now=int(time.time()) if now is None else now
    valid=isinstance(value,dict) and set(value)==RESULT_KEYS and value.get('format')=='CLSES-adapter-result/v1' and value.get('request_id')==request['request_id'] and value.get('adapter_id')==manifest['id'] and value.get('adapter_digest')==manifest['digest'] and value.get('evidence_type')==request['evidence_type'] and request['evidence_type'] in manifest['capabilities'] and value.get('passed') is True and isinstance(value.get('measurements'),dict) and bool(value['measurements']) and isinstance(value.get('raw_evidence_sha256'),str) and len(value['raw_evidence_sha256'])==64 and isinstance(value.get('observed_at'),int) and isinstance(value.get('expires_at'),int) and value['observed_at']<=now<=value['expires_at']<=request['deadline']
    if not valid:raise ValueError('adapter result is invalid, failing, mismatched, or stale')
    return value

def run_adapter(manifest,request,now=None):
    manifest=validate_manifest(manifest);request=validate_request(request,now)
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);request_path=root/'request.json';output_path=root/'result.json';request_path.write_bytes(canonical(request));argv=[str(x).replace('{request}',str(request_path)).replace('{output}',str(output_path)).replace('{adapter_id}',manifest['id']).replace('{adapter_digest}',manifest['digest']).replace('{trust_anchor}',manifest['trust_anchor']) for x in manifest['command']]
        env=dict(os.environ);package_parent=str(Path(__file__).resolve().parent.parent);env['PYTHONPATH']=package_parent+(os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        cp=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=manifest['timeout_seconds'],env=env)
        if cp.returncode:raise RuntimeError('adapter process failed')
        raw=output_path.read_text() if output_path.exists() else cp.stdout
        try:value=json.loads(raw)
        except json.JSONDecodeError as exc:raise ValueError('adapter did not return JSON') from exc
        return validate_result(value,manifest,request,now)

def as_evidence(result,request):
    return {'id':'evidence-'+request['request_id'],'control_id':request['control_id'],'artifact_id':request['artifact_id'],'type':request['evidence_type'],'adapter_id':result['adapter_id'],'adapter_digest':result['adapter_digest'],'raw_digest':result['raw_evidence_sha256'],'observed_at':result['observed_at'],'expires_at':result['expires_at'],'environment_id':request['environment_id'],'passed':result['passed'],'measurements':result['measurements']}
