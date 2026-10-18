"""Thin, deterministic operator journey over intake, copilot, and lifecycle controls."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

from .autonomy import AutonomousLoop
from .copilot import LifecycleCopilot
from .engine import Engine
from .intake import answer as answer_intake
from .intake import public_result as intake_result
from .intake import reassess as reassess_intake
from .intake import start as start_intake
from .store import digest, read, write


WORKFLOW_FORMAT = "CLSES-guided-operator/v1"
PACKET_FORMAT = "CLSES-authorization-request-packet/v1"
STEPS = (
    "understand_the_need",
    "authorize_product_baseline",
    "authorize_engineering",
    "engineer_and_verify",
    "authorize_build",
    "accept_and_deploy",
    "operate_and_reassess",
)


def _validate_schema(name, value):
    schema = json.loads((Path(__file__).resolve().parent / "schemas" / name).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        raise ValueError("normative " + name + " failure: " + errors[0].message)


class GuidedOperator:
    """A single human-facing journey; all authority remains in LifecycleCopilot."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.copilot = LifecycleCopilot(self.root)
        self.engine = self.copilot.engine
        self.store = self.copilot.store
        self.base = self.store.state / "operator"
        self.workflow_path = self.base / "workflow.json"

    @classmethod
    def setup(cls, root, system_id="new-system", purpose="Provide a reliable service", beneficiary="users"):
        Engine(root).init(system_id=system_id, purpose=purpose, beneficiary=beneficiary)
        return cls(root)

    def _workflow(self):
        return read(self.workflow_path) if self.workflow_path.exists() else None

    def _save_workflow(self, workflow):
        workflow["updated_at"] = int(time.time())
        core = {key: value for key, value in workflow.items() if key != "state_digest"}
        workflow["state_digest"] = digest(core)
        _validate_schema("guided-operator-state.schema.json", workflow)
        write(self.workflow_path, workflow)
        return workflow

    def begin(self, profile, context=None, profile_dir=None, now=None):
        if self.workflow_path.exists():
            raise ValueError("guided workflow already exists; answer or reassess the current intake")
        timestamp = int(time.time()) if now is None else int(now)
        intake = start_intake(profile, context or {}, profile_dir, timestamp)
        workflow = {
            "format": WORKFLOW_FORMAT,
            "journey_id": str(uuid.uuid4()),
            "profile": profile,
            "intake": intake,
            "authorization_packet_ids": [],
            "created_at": timestamp,
            "updated_at": timestamp,
            "state_digest": "",
        }
        self._save_workflow(workflow)
        return self.status()

    def answer(self, answers, now=None):
        workflow = self._workflow()
        if workflow is None:
            raise ValueError("begin the guided workflow before answering intake questions")
        workflow["intake"] = answer_intake(workflow["intake"], answers, now)
        self._save_workflow(workflow)
        return self.status()

    def reassess(self, change, now=None):
        workflow = self._workflow()
        if workflow is None:
            raise ValueError("begin the guided workflow before recording a change")
        workflow["intake"] = reassess_intake(workflow["intake"], change, now)
        self._save_workflow(workflow)
        return self.status()

    def open_session(self, principal, credential, ttl=3600):
        return self.copilot.open_session(principal, credential, ttl)

    def _pending_proposals(self):
        values = []
        folder = self.copilot.base / "decisions"
        for path in sorted(folder.glob("*.json")) if folder.exists() else []:
            pointer = read(path)
            if pointer.get("status") != "proposed":
                continue
            proposal = self.store.get(pointer["proposal_record"], "copilot_decision_proposal", "agent")["payload"]
            values.append(proposal)
        return values

    @staticmethod
    def _baseline_scope(baseline):
        excluded = {"decision", "authorization_digest", "authorized_at", "assumptions", "resolved_facts"}
        return "baseline:" + digest({key: value for key, value in baseline.items() if key not in excluded})

    def _baseline_authorized(self, workflow=None):
        workflow = workflow or self._workflow()
        baseline = workflow.get("intake", {}).get("baseline") if workflow else None
        if not baseline or baseline.get("decision") != "authorized":
            return False
        try:
            authorization = self.engine.policy.authorization(self._baseline_scope(baseline), "product", "system", "owner")
            return baseline.get("authorization_digest") == authorization[0]
        except PermissionError:
            return False

    def _synchronize_execution_facts(self):
        workflow = self._workflow()
        if workflow is None or workflow["intake"].get("baseline") is None:
            return
        lifecycle = self.copilot.status();runs = lifecycle.get("runs", [])
        if not runs or runs[-1]["phase"] not in ("awaiting_build", "awaiting_release", "complete"):
            return
        intake = workflow["intake"];baseline = intake["baseline"];now = int(time.time());changed = False
        _, spec, spec_digest = self.engine._spec()
        values = {"architecture_status": "implemented_and_verified_against_current_specification"}
        components = spec.get("components", [])
        if components and all(Path(item).suffix == ".py" for item in components):
            values["implementation_language"] = "Python"
        for fact_id, value in values.items():
            current = intake.get("facts", {}).get(fact_id, {}).get("value")
            if current == value:
                continue
            assumption = intake.get("assumptions", {}).get(fact_id)
            if assumption and assumption.get("status") == "active":
                assumption.update({"status": "replaced_by_execution_evidence", "last_reviewed_at": now})
            intake.setdefault("facts", {})[fact_id] = {"value": value, "source": "execution_evidence:" + spec_digest, "confidence": 1.0, "recorded_at": now, "status": "current"}
            intake["deferred"] = [item for item in intake.get("deferred", []) if item != fact_id]
            baseline.setdefault("resolved_facts", {})[fact_id] = {"value": value, "source": "execution_evidence:" + spec_digest, "recorded_at": now}
            changed = True
        if changed:
            baseline["assumptions"] = [item for item in intake.get("assumptions", {}).values() if item.get("status") == "active"]
            intake["state_digest"] = digest({key: value for key, value in intake.items() if key != "state_digest"})
            self._save_workflow(workflow)

    def _is_authorized(self, scope, item):
        signer = {"product": "owner", "engineering": "engineering-reviewer", "release": "release-owner"}[item["kind"]]
        try:
            self.engine.policy.authorization(scope, item["kind"], item["subject"], signer)
            return True
        except PermissionError:
            return False

    def _authorization_summary(self):
        expected = self.copilot._expected_scopes()
        pending = self._pending_proposals()
        by_scope = {
            proposal["payload"]["scope"]: proposal
            for proposal in pending
            if proposal.get("kind") == "authorization"
        }
        requests = []
        for scope, item in sorted(expected.items()):
            principal = "engineering-reviewer" if item["kind"] == "engineering" else "release-owner"
            if self._is_authorized(scope, item):
                state = "authorized"
            elif scope in by_scope:
                state = "awaiting_explicit_decision"
            else:
                state = "ready_to_prepare"
            requests.append({
                "scope": scope,
                "purpose": item["purpose"],
                "required_principal": principal,
                "state": state,
                "decision_id": by_scope.get(scope, {}).get("decision_id"),
            })
        return requests

    def _plain_evidence(self, lifecycle):
        if lifecycle.get("stage") == "complete":
            verdict = self.engine.verify()
            return {
                "available": True,
                "summary": "The controlled cycle is closed and its current verification is " + ("valid." if verdict["valid"] else "not valid."),
                "verification": {"valid": verdict["valid"], "intrinsic": verdict["intrinsic"], "relational": verdict["relational"]},
            }
        pending = lifecycle.get("pending")
        if not pending or lifecycle.get("stage") != "awaiting_release":
            return {"available": False, "summary": "No release candidate is waiting for review."}
        build = self.store.get(pending["build_digest"], "build", "builder")["payload"]
        test = self.store.get(build["test_evidence_digest"], "test_evidence", "builder")["payload"]
        return {
            "available": True,
            "summary": "The exact release candidate was built and its recorded test run passed." if test["exit_code"] == 0 else "The recorded test run failed; release must remain blocked.",
            "artifact": pending["artifact_digest"],
            "test_result": "passed" if test["exit_code"] == 0 else "failed",
            "test_evidence": build["test_evidence_digest"],
        }

    def status(self):
        workflow = self._workflow()
        lifecycle = self.copilot.status()
        requests = self._authorization_summary()
        intake = intake_result(workflow["intake"]) if workflow else None
        run = lifecycle["runs"][-1] if lifecycle["runs"] else None

        if workflow is None:
            step = STEPS[0]
            summary = "Tell me what you want to build. I will ask only for facts required to form a viable proposal."
            next_action = {"action": "begin", "who": "product owner", "instruction": "Start the guided intake with a lifecycle profile."}
            complete = 0
        elif intake["question_count"]:
            step = STEPS[0]
            summary = "I need " + str(intake["question_count"]) + " consolidated answer group(s) before I can prepare the baseline."
            next_action = {"action": "answer", "who": "product owner", "instruction": "Answer the displayed intake questions; answers remain non-authoritative."}
            complete = 0
        elif not self._baseline_authorized(workflow):
            step = STEPS[1]
            summary = "The minimum viable baseline is ready, but product intent has not been authorized."
            next_action = {"action": "authorizations", "who": "product owner", "instruction": "Review and explicitly authorize or reject the exact product baseline before engineering."}
            complete = 1
        elif run is None:
            step = STEPS[2]
            summary = "The product baseline is authorized, but no engineering mandate has been authorized."
            next_action = {"action": "mandate", "who": "engineering reviewer", "instruction": "Prepare a bounded engineering mandate, then explicitly approve or reject its exact challenge."}
            complete = 2
        elif run["phase"] == "engineering":
            step = STEPS[3]
            summary = "Autonomous engineering is authorized and ready to continue inside its mandate."
            next_action = {"action": "continue", "who": "operator", "instruction": "Resume the run; the agent may execute engineering but cannot authorize consequential transitions."}
            complete = 3
        elif run["phase"] == "awaiting_build":
            step = STEPS[4]
            build_requests = [item for item in requests if item["scope"].startswith("build:")]
            if build_requests and all(item["state"] == "authorized" for item in build_requests):
                summary = "The exact build authorization is recorded. Engineering can continue to the release candidate."
                next_action = {"action": "continue", "who": "operator", "instruction": "Resume the authorized run."}
            else:
                summary = "Engineering evidence is ready. The exact change set needs build authorization."
                next_action = {"action": "authorizations", "who": "engineering reviewer", "instruction": "Prepare and decide the consolidated authorization request."}
            complete = 4
        elif run["phase"] == "awaiting_release":
            step = STEPS[5]
            release_requests = [item for item in requests if item["scope"].startswith(("accept:", "deploy:"))]
            if release_requests and all(item["state"] == "authorized" for item in release_requests):
                summary = "Artifact acceptance and deployment authorization are recorded. The controlled deployment can continue."
                next_action = {"action": "continue", "who": "operator", "instruction": "Resume the run to deploy, observe, assess, and close the cycle."}
            else:
                summary = "The release candidate passed its recorded tests and now needs acceptance and deployment decisions."
                next_action = {"action": "authorizations", "who": "release owner", "instruction": "Review one consolidated packet containing the separate acceptance and deployment decisions."}
            complete = 5
        elif run["phase"] == "complete":
            step = STEPS[6]
            summary = "Cycle closed; continuous monitoring and change-triggered reassessment are active."
            next_action = {"action": "monitor", "who": "operations and outcome authorities", "instruction": "Collect current production evidence and reassess when conditions change or evidence expires."}
            complete = 7
        else:
            step = STEPS[3]
            summary = "The engineering run needs attention: " + run["phase"].replace("_", " ") + "."
            next_action = {"action": "review", "who": "engineering reviewer", "instruction": lifecycle["next_action"].capitalize() + "."}
            complete = 3

        return {
            "headline": summary,
            "current_step": step,
            "progress": {"completed": complete, "total": len(STEPS), "steps": list(STEPS)},
            "next": next_action,
            "intake": intake,
            "authorization_requests": requests,
            "evidence": self._plain_evidence(lifecycle),
            "technical_stage": lifecycle["stage"],
            "authority_notice": "Conversation, silence, and agent actions never authorize. Each consequential decision requires the named human principal and its exact one-time challenge.",
        }

    def prepare_authorizations(self, session_id, token, human_evidence=None):
        session = self.copilot._session(session_id, token)
        principal = session["principal"]
        expected = self.copilot._expected_scopes()
        existing = {
            proposal["payload"]["scope"]: proposal
            for proposal in self._pending_proposals()
            if proposal.get("kind") == "authorization"
        }
        proposals = []
        deferred = []
        for scope, item in sorted(expected.items()):
            required = {"product": "owner", "engineering": "engineering-reviewer", "release": "release-owner"}[item["kind"]]
            if required != principal:
                if not self._is_authorized(scope, item):
                    deferred.append({"scope": scope, "required_principal": required})
                continue
            if self._is_authorized(scope, item):
                continue
            proposal = existing.get(scope) or self.copilot.propose_authorization(session_id, token, scope, human_evidence)
            proposals.append(proposal)
        if not proposals:
            raise ValueError("no undecided active authorization requests are available for " + principal)
        created = int(time.time())
        packet = {
            "format": PACKET_FORMAT,
            "packet_id": str(uuid.uuid4()),
            "required_principal": principal,
            "created_at": created,
            "status": "awaiting_explicit_decisions",
            "items": [{
                "decision_id": item["decision_id"],
                "scope": item["payload"]["scope"],
                "summary": item["summary"],
                "evidence": item["payload"]["evidence"],
                "approve_exactly": item["challenge"],
                "reject_exactly": item["reject_challenge"],
            } for item in proposals],
            "deferred_to_other_principals": deferred,
            "authority_notice": "This packet consolidates review only. Every item remains a separate, exact, non-replayable decision.",
            "packet_digest": "",
        }
        packet["packet_digest"] = digest({key: value for key, value in packet.items() if key != "packet_digest"})
        _validate_schema("authorization-request-packet.schema.json", packet)
        write(self.base / "packets" / (packet["packet_id"] + ".json"), packet)
        workflow = self._workflow()
        if workflow is not None and packet["packet_id"] not in workflow["authorization_packet_ids"]:
            workflow["authorization_packet_ids"].append(packet["packet_id"])
            self._save_workflow(workflow)
        return packet

    def propose_mandate(self, session_id, token, mandate):
        workflow = self._workflow()
        if workflow is None or workflow["intake"]["baseline"] is None:
            raise PermissionError("a complete minimum viable baseline is required before an engineering mandate")
        if not self._baseline_authorized(workflow):
            raise PermissionError("the exact product baseline requires explicit owner authorization before an engineering mandate")
        return self.copilot.propose_mandate(session_id, token, mandate)

    def register_driver(self, session_id, token, name, kind="generic", argv=None):
        session = self.copilot._session(session_id, token)
        if session["principal"] != "owner":
            raise PermissionError("owner session required to register an execution driver")
        return AutonomousLoop(self.root).register_driver(name, kind, argv, session["principal"])

    def decide(self, session_id, token, decision_id, outcome, confirmation):
        result = self.copilot.decide(session_id, token, decision_id, outcome, confirmation)
        effect = result.get("effect") or {}
        if outcome == "approve" and effect.get("scope", "").startswith("baseline:"):
            workflow = self._workflow();baseline = workflow["intake"]["baseline"]
            if effect["scope"] != self._baseline_scope(baseline):raise RuntimeError("authorized baseline no longer matches current intake")
            baseline.update({"decision": "authorized", "authorization_digest": effect["authorization_digest"], "authorized_at": int(time.time())})
            intake = workflow["intake"];intake["state_digest"] = digest({key:value for key,value in intake.items() if key != "state_digest"});self._save_workflow(workflow)
        return result

    def continue_run(self, session_id, token, run_id):
        result = self.copilot.resume(session_id, token, run_id);self._synchronize_execution_facts();return result

    def turn(self, session_id, token, message, data=None):
        """Deterministic conversational router; ambiguous language never mutates state."""
        self.copilot._session(session_id, token)
        text = message.strip()
        lower = text.lower()
        if not text:
            raise ValueError("message must not be empty")
        if lower in {"status", "where are we?", "what is next?", "next", "help"}:
            return {"response": self.status()["headline"], "view": self.status(), "authoritative": False}
        if lower == "begin intake":
            data = data or {}
            return {"response": "The guided intake has started.", "view": self.begin(data.get("profile", "base-production"), data.get("context"), data.get("profile_dir")), "authoritative": False}
        if lower == "answer intake":
            return {"response": "I recorded the requested facts as non-authoritative intake input.", "view": self.answer(data or {}), "authoritative": False}
        if lower == "reassess intake":
            return {"response": "I reopened only the intake facts affected by the declared change.", "view": self.reassess(data or {}), "authoritative": False}
        if lower == "prepare authorizations":
            packet = self.prepare_authorizations(session_id, token, data or {})
            return {"response": "I prepared one review packet. Its items still require separate exact decisions.", "packet": packet, "view": self.status(), "authoritative": False}
        if lower in {"approve", "i approve", "authorize", "i authorize"} or any(word in lower for word in (" approve ", " authorize ")):
            return {"response": "I cannot treat conversation as authority. Use the exact challenge shown in the authorization packet.", "view": self.status(), "authoritative": False}
        return {"response": "I did not change lifecycle state because the request was ambiguous. Say status, begin intake, answer intake, reassess intake, or prepare authorizations.", "view": self.status(), "authoritative": False}
