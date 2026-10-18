from __future__ import annotations
import argparse,json,sys
from .engine import Engine
from .autonomy import AutonomousLoop

def main():
    parser=argparse.ArgumentParser(prog='clses-v1');parser.add_argument('--root',default='.');commands=parser.add_subparsers(dest='command',required=True)
    item=commands.add_parser('init');item.add_argument('--spec');item.add_argument('--system-id',default='new-system');item.add_argument('--purpose',default='Provide a reliable service');item.add_argument('--beneficiary',default='users');item.add_argument('--template-manifest');item.add_argument('--github-owner')
    item=commands.add_parser('authorize');item.add_argument('--scope',required=True);item.add_argument('--kind',choices=['engineering','release'],required=True);item.add_argument('--signer',required=True);item.add_argument('--subject',required=True)
    item=commands.add_parser('driver-register');item.add_argument('--name',required=True);item.add_argument('--kind',choices=['codex','generic'],required=True);item.add_argument('--argv-json')
    item=commands.add_parser('mandate');item.add_argument('--run-id',required=True);item.add_argument('--objective',required=True);item.add_argument('--driver',required=True);item.add_argument('--allowed-path',action='append',required=True);item.add_argument('--requirement',action='append',required=True);item.add_argument('--max-iterations',type=int,default=5);item.add_argument('--max-changes',type=int,default=12);item.add_argument('--max-bytes',type=int,default=50000);item.add_argument('--expires-at',type=int,default=4102444800)
    item=commands.add_parser('autonomy-run');item.add_argument('--run-id',required=True)
    item=commands.add_parser('spec-propose');item.add_argument('--change-id',required=True);item.add_argument('--spec',required=True)
    item=commands.add_parser('spec-apply');item.add_argument('--change-id',required=True)
    item=commands.add_parser('request');item.add_argument('--work-id',required=True);item.add_argument('--instruction',required=True);item.add_argument('--path',required=True);item.add_argument('--content',required=True);item.add_argument('--requirement',action='append',required=True);item.add_argument('--expected-sha256')
    item=commands.add_parser('execute');item.add_argument('--work-id',required=True)
    for name in ('plan','build','complete','verify'):commands.add_parser(name)
    args=parser.parse_args();engine=Engine(args.root)
    try:
        if args.command=='init':result=engine.init(args.spec,args.system_id,args.purpose,args.beneficiary,args.template_manifest,args.github_owner)
        elif args.command=='authorize':result=engine.authorize(args.scope,args.kind,args.signer,args.subject)
        elif args.command=='driver-register':result=AutonomousLoop(args.root).register_driver(args.name,args.kind,json.loads(args.argv_json) if args.argv_json else None)
        elif args.command=='mandate':result=engine.mandate(args.run_id,args.objective,args.driver,args.allowed_path,args.requirement,args.max_iterations,args.max_changes,args.max_bytes,args.expires_at)
        elif args.command=='autonomy-run':result=AutonomousLoop(args.root).run(args.run_id)
        elif args.command=='spec-propose':result=engine.propose_spec(args.change_id,args.spec)
        elif args.command=='spec-apply':result=engine.apply_spec(args.change_id)
        elif args.command=='request':result=engine.request(args.work_id,args.instruction,args.path,args.content,args.requirement,args.expected_sha256)
        elif args.command=='execute':result=engine.execute(args.work_id)
        elif args.command=='plan':result=engine.plan()
        elif args.command=='build':result=engine.build()
        elif args.command=='complete':result=engine.complete()
        else:result=engine.verify()
        print(json.dumps(result,indent=2));return 0 if result.get('valid',True) else 1
    except (ValueError,PermissionError,RuntimeError,FileNotFoundError,KeyError) as exc:print(json.dumps({'error':str(exc)}),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
