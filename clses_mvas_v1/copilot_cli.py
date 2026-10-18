"""Command interface for the CLSES Lifecycle Copilot."""
from __future__ import annotations
import argparse,json,sys
from .copilot import LifecycleCopilot

def main():
    parser=argparse.ArgumentParser(prog='clses-copilot');parser.add_argument('--root',default='.');sub=parser.add_subparsers(dest='command',required=True)
    item=sub.add_parser('session-open');item.add_argument('--principal',required=True);item.add_argument('--credential-file',required=True);item.add_argument('--ttl',type=int,default=3600)
    item=sub.add_parser('status')
    item=sub.add_parser('facilitator-register');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--name',required=True);item.add_argument('--kind',choices=['codex','generic'],required=True);item.add_argument('--argv-json')
    item=sub.add_parser('say');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--message',required=True);item.add_argument('--facilitator')
    item=sub.add_parser('mandate-propose');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--file',required=True)
    item=sub.add_parser('authorization-propose');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--scope',required=True);item.add_argument('--evidence-file')
    item=sub.add_parser('specification-propose');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--change-id',required=True);item.add_argument('--file',required=True)
    item=sub.add_parser('specification-apply');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--change-id',required=True)
    item=sub.add_parser('decide');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--decision-id',required=True);item.add_argument('--outcome',choices=['approve','reject'],required=True);item.add_argument('--confirmation',required=True)
    item=sub.add_parser('resume');item.add_argument('--session',required=True);item.add_argument('--token',required=True);item.add_argument('--run-id',required=True)
    args=parser.parse_args()
    try:
        copilot=LifecycleCopilot(args.root)
        if args.command=='session-open':result=copilot.open_session(args.principal,open(args.credential_file).read(),args.ttl)
        elif args.command=='status':result=copilot.status()
        elif args.command=='facilitator-register':result=copilot.register_facilitator(args.session,args.token,args.name,args.kind,json.loads(args.argv_json) if args.argv_json else None)
        elif args.command=='say':result=copilot.say(args.session,args.token,args.message,args.facilitator)
        elif args.command=='mandate-propose':result=copilot.propose_mandate(args.session,args.token,json.load(open(args.file)))
        elif args.command=='authorization-propose':result=copilot.propose_authorization(args.session,args.token,args.scope,json.load(open(args.evidence_file)) if args.evidence_file else None)
        elif args.command=='specification-propose':result=copilot.propose_specification(args.session,args.token,args.change_id,args.file)
        elif args.command=='specification-apply':result=copilot.apply_specification(args.session,args.token,args.change_id)
        elif args.command=='decide':result=copilot.decide(args.session,args.token,args.decision_id,args.outcome,args.confirmation)
        else:result=copilot.resume(args.session,args.token,args.run_id)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,PermissionError,RuntimeError,FileNotFoundError,KeyError) as exc:print(json.dumps({'error':str(exc)}),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
