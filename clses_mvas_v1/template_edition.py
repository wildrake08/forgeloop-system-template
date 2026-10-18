"""Fail-closed adoption and verification for a GitHub-copied CLSES scaffold."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from .store import digest,read,write,Store

FORMAT='CLSES-template-manifest/v1'
DEFAULT_MANIFEST='.clses-template/template-manifest.json'
MUTABLE_PREFIXES=('src/','tests/')
MUTABLE_FILES=('.github/CODEOWNERS',)
LOCAL_TOP_LEVEL={'.venv','venv','.direnv','.pytest_cache','.mypy_cache','.ruff_cache','htmlcov','build','dist'}
LOCAL_FILES={'.coverage','.DS_Store'}

def _mutable(name):return name.startswith(MUTABLE_PREFIXES) or name in MUTABLE_FILES

def _excluded(relative):
    parts=relative.parts
    top=parts[0] if parts else ''
    return (not parts or top in ('.git','.clses-v1') or top in LOCAL_TOP_LEVEL or top.endswith('.egg-info') or
            str(relative) in LOCAL_FILES or '__pycache__' in parts or relative.suffix=='.pyc' or
            str(relative)==DEFAULT_MANIFEST)

def inventory(root,include_mutable=True):
    root=Path(root).resolve();items=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if _excluded(relative):continue
        if path.is_symlink():raise ValueError('template may not contain symbolic links: '+str(relative))
        if not path.is_file():continue
        name=str(relative)
        if not include_mutable and _mutable(name):continue
        items.append({'path':name,'sha256':digest(path.read_bytes()),'size':path.stat().st_size})
    return items

def generate_manifest(root,output=None):
    root=Path(root).resolve();output=Path(output) if output else root/DEFAULT_MANIFEST
    entries=inventory(root);core={'format':FORMAT,'version':'4.6.2','entries':entries,'immutable_entries':[x for x in entries if not _mutable(x['path'])]}
    manifest={**core,'manifest_digest':digest(core)};write(output,manifest);return manifest

def verify_scaffold(root,manifest=DEFAULT_MANIFEST,strict=True):
    root=Path(root).resolve();path=Path(manifest);path=path if path.is_absolute() else root/path
    errors=[]
    try:
        value=read(path);core={k:value[k] for k in ('format','version','entries','immutable_entries')}
        if value.get('format')!=FORMAT or value.get('version')!='4.6.2':errors.append('unsupported manifest format or version')
        if value.get('manifest_digest')!=digest(core):errors.append('manifest digest mismatch')
        expected=value['entries'] if strict else value['immutable_entries'];actual=inventory(root,include_mutable=strict)
        if expected!=actual:errors.append('repository inventory differs from the signed release scaffold')
    except (FileNotFoundError,ValueError,KeyError,json.JSONDecodeError) as exc:errors.append(str(exc))
    return {'valid':not errors,'strict':strict,'manifest_digest':value.get('manifest_digest') if 'value' in locals() else None,'entries':len(actual) if 'actual' in locals() else 0,'errors':errors}

def adopt_scaffold(root,manifest,github_owner):
    result=verify_scaffold(root,manifest,strict=True)
    if not result['valid']:raise ValueError('template scaffold integrity failure: '+'; '.join(result['errors']))
    if not re.fullmatch(r'@[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:/[A-Za-z0-9_.-]+)?',github_owner or ''):raise ValueError('github owner must be @user or @organization/team')
    path=Path(root).resolve()/'.github/CODEOWNERS';path.write_text('* '+github_owner+'\n')
    return result,{'github_owner':github_owner,'codeowners_sha256':digest(path.read_bytes())}

def workspace_status(root):
    root=Path(root).resolve();template=verify_scaffold(root,strict=False)
    if not (root/'.clses-v1').exists():return {**template,'state':'awaiting_initialization','action':'Run the bootstrap command before changing files.'}
    store=Store(root);ledger,count=store.verify_ledger();checks={'template_integrity':template['valid'],'ledger_valid':ledger}
    try:
        _,baseline=store.deref('baseline','baseline','assessor');payload=baseline['payload'];checks['template_binding']=payload.get('template_manifest_digest')==template['manifest_digest'];custom=payload.get('template_customizations',{});codeowners=root/'.github/CODEOWNERS';checks['customization_binding']=bool(custom.get('github_owner')) and custom.get('codeowners_sha256')==digest(codeowners.read_bytes());from .engine import Engine
        checks['governed_snapshot_current']=payload['snapshot']==Engine(root)._snapshot()
    except (FileNotFoundError,ValueError,KeyError,PermissionError):checks.update({'template_binding':False,'governed_snapshot_current':False})
    valid=all(checks.values());return {'valid':valid,'state':'ready' if valid else 'change_detected_or_invalid','checks':checks,'ledger_records':count,'errors':template['errors']}

def main():
    parser=argparse.ArgumentParser(prog='clses-template');parser.add_argument('--root',default='.');commands=parser.add_subparsers(dest='command',required=True)
    item=commands.add_parser('bootstrap');item.add_argument('--system-id',required=True);item.add_argument('--purpose',required=True);item.add_argument('--beneficiary',required=True);item.add_argument('--github-owner',required=True);item.add_argument('--spec')
    commands.add_parser('check');commands.add_parser('verify-scaffold');commands.add_parser('generate-manifest')
    args=parser.parse_args();root=Path(args.root).resolve()
    try:
        if args.command=='bootstrap':
            from .engine import Engine
            result=Engine(root).init(args.spec,args.system_id,args.purpose,args.beneficiary,root/DEFAULT_MANIFEST,args.github_owner)
        elif args.command=='check':result=workspace_status(root)
        elif args.command=='verify-scaffold':result=verify_scaffold(root,strict=not (root/'.clses-v1').exists())
        else:result=generate_manifest(root)
        print(json.dumps(result,indent=2));return 0 if result.get('valid',True) else 1
    except (ValueError,PermissionError,RuntimeError,FileNotFoundError,KeyError) as exc:print(json.dumps({'error':str(exc)}));return 1
if __name__=='__main__':raise SystemExit(main())
