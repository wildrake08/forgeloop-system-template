"""One guided command surface for non-technical CLSES operation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .guided_operator import GuidedOperator
from .discovery import discover_environment
from .onboarding import apply_onboarding, list_templates, plan_onboarding
from .visual_operator import serve


def _json(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(prog="clses-operator", description="Guided CLSES lifecycle: intake, status, decisions, and continuation")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    item = sub.add_parser("setup", help="initialize an empty system workspace")
    item.add_argument("--system-id", default="new-system")
    item.add_argument("--purpose", default="Provide a reliable service")
    item.add_argument("--beneficiary", default="users")
    sub.add_parser("templates", help="list guided onboarding templates")
    item = sub.add_parser("discover", help="inspect the local environment without reading secrets")
    item.add_argument("--source-root")
    item.add_argument("--output")
    item = sub.add_parser("onboard-plan", help="prepare a non-authoritative onboarding plan")
    item.add_argument("--template", required=True)
    item.add_argument("--answers")
    item.add_argument("--discovery")
    item.add_argument("--accept-discovery", action="store_true")
    item = sub.add_parser("onboard", help="initialize and begin from a completed onboarding template")
    item.add_argument("--template", required=True)
    item.add_argument("--answers", required=True)
    item.add_argument("--discovery")
    item.add_argument("--accept-discovery", action="store_true")
    item = sub.add_parser("serve", help="run the loopback-only visual operator")
    item.add_argument("--host", default="127.0.0.1")
    item.add_argument("--port", type=int, default=8765)
    item = sub.add_parser("begin", help="begin minimum-viability intake")
    item.add_argument("--profile", required=True)
    item.add_argument("--context")
    item.add_argument("--profile-dir")
    item = sub.add_parser("answer", help="answer only the currently requested intake facts")
    item.add_argument("--file", required=True)
    item = sub.add_parser("reassess", help="reopen intake facts affected by a declared change")
    item.add_argument("--file", required=True)
    sub.add_parser("status", help="show one plain-language lifecycle view")
    item = sub.add_parser("session-open", help="authenticate a human authority")
    item.add_argument("--principal", required=True)
    item.add_argument("--credential-file", required=True)
    item.add_argument("--ttl", type=int, default=3600)
    item = sub.add_parser("session-close", help="immediately revoke the current bearer session")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item = sub.add_parser("turn", help="use the deterministic conversational workflow")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--message", required=True)
    item.add_argument("--data-file")
    item = sub.add_parser("driver-register", help="register a replaceable engineering agent")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--name", required=True)
    item.add_argument("--kind", choices=["codex", "generic"], required=True)
    item.add_argument("--argv-json")
    item = sub.add_parser("mandate", help="prepare a bounded engineering mandate")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--file", required=True)
    item = sub.add_parser("authorizations", help="prepare one consolidated review packet")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--evidence-file")
    item = sub.add_parser("decide", help="make one exact decision from a review packet")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--decision-id", required=True)
    item.add_argument("--outcome", choices=["approve", "reject"], required=True)
    item.add_argument("--confirmation", required=True)
    item.add_argument("--reason", help="required rationale when rejecting")
    item = sub.add_parser("mandate-revoke", help="revoke an active autonomous engineering mandate")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--run-id", required=True)
    item.add_argument("--reason", required=True)
    item.add_argument("--confirmation", required=True)
    item.add_argument("--superseding-run-id")
    item = sub.add_parser("continue", help="continue an authorized autonomous run")
    item.add_argument("--session", required=True)
    item.add_argument("--token", required=True)
    item.add_argument("--run-id", required=True)
    args = parser.parse_args()

    try:
        if args.command == "templates":
            result = list_templates()
        elif args.command == "discover":
            result = discover_environment(args.source_root or args.root)
            if args.output:
                from .store import write
                write(args.output, result)
        elif args.command == "onboard-plan":
            result = plan_onboarding(args.template, _json(args.answers) if args.answers else {}, _json(args.discovery) if args.discovery else None, args.accept_discovery)
        elif args.command == "onboard":
            result = apply_onboarding(args.root, args.template, _json(args.answers), _json(args.discovery) if args.discovery else None, args.accept_discovery)
        elif args.command == "serve":
            serve(args.root, args.host, args.port)
            return 0
        elif args.command == "setup":
            operator = GuidedOperator.setup(args.root, args.system_id, args.purpose, args.beneficiary)
            result = operator.status()
        else:
            operator = GuidedOperator(args.root)
            if args.command == "begin":
                result = operator.begin(args.profile, _json(args.context) if args.context else {}, args.profile_dir)
            elif args.command == "answer":
                result = operator.answer(_json(args.file))
            elif args.command == "reassess":
                result = operator.reassess(_json(args.file))
            elif args.command == "status":
                result = operator.status()
            elif args.command == "session-open":
                result = operator.open_session(args.principal, Path(args.credential_file).read_text(), args.ttl)
            elif args.command == "session-close":
                result = operator.close_session(args.session, args.token)
            elif args.command == "turn":
                result = operator.turn(args.session, args.token, args.message, _json(args.data_file) if args.data_file else None)
            elif args.command == "driver-register":
                result = operator.register_driver(args.session, args.token, args.name, args.kind, json.loads(args.argv_json) if args.argv_json else None)
            elif args.command == "mandate":
                result = operator.propose_mandate(args.session, args.token, _json(args.file))
            elif args.command == "authorizations":
                result = operator.prepare_authorizations(args.session, args.token, _json(args.evidence_file) if args.evidence_file else None)
            elif args.command == "decide":
                result = operator.decide(args.session, args.token, args.decision_id, args.outcome, args.confirmation, args.reason)
            elif args.command == "mandate-revoke":
                result = operator.revoke_mandate(args.session,args.token,args.run_id,args.reason,args.confirmation,args.superseding_run_id)
            else:
                result = operator.continue_run(args.session, args.token, args.run_id)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, PermissionError, RuntimeError, FileNotFoundError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
