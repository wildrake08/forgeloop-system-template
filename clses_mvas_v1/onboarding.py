"""Reusable, human-reviewed onboarding templates for the guided operator."""
from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from .guided_operator import GuidedOperator
from .store import digest


ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "onboarding_templates"
SCHEMA_DIR = ROOT / "schemas"


def _validate(name, value):
    schema = json.loads((SCHEMA_DIR / name).read_text())
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ValueError("normative " + name + " failure: " + errors[0].message)


def list_templates(template_dir=TEMPLATE_DIR):
    return [load_template(path, template_dir) for path in sorted(Path(template_dir).glob("*.json"))]


def load_template(template, template_dir=TEMPLATE_DIR):
    path = Path(template)
    if not path.exists():
        path = Path(template_dir) / (str(template) + ".json")
    value = json.loads(path.read_text())
    _validate("onboarding-template.schema.json", value)
    return value


def plan_onboarding(template, answers=None, discovery=None, accept_discovery=False, template_dir=TEMPLATE_DIR):
    template = load_template(template, template_dir) if not isinstance(template, dict) else template
    _validate("onboarding-template.schema.json", template)
    answers = answers or {}
    allowed = {item["fact_id"] for item in template["inputs"]}
    unknown = set(answers) - allowed
    if unknown:
        raise ValueError("onboarding answers are not declared by the template: " + ",".join(sorted(unknown)))
    facts = dict(template["starter_facts"])
    discovery_digest = None
    if discovery is not None:
        _validate("environment-discovery.schema.json", discovery)
        if discovery["report_digest"] != digest({key: value for key, value in discovery.items() if key != "report_digest"}):
            raise ValueError("environment discovery digest mismatch")
        discovery_digest = discovery["report_digest"]
        if accept_discovery:
            for key in ("system_name", "system_class", "operating_conditions"):
                if key in discovery["suggested_facts"]:
                    facts[key] = discovery["suggested_facts"][key]
    facts.update({key: value for key, value in answers.items() if value is not None and value != ""})
    if "system_name" in facts and "system_id" not in facts:
        facts["system_id"] = re.sub(r"[^a-z0-9]+", "-", facts["system_name"].lower()).strip("-") or "new-system"
    if "problem" in facts and "purpose" not in facts:
        facts["purpose"] = "Address: " + facts["problem"]
    missing = [item for item in template["inputs"] if item["required"] and item["fact_id"] not in facts]
    result = {
        "format": "CLSES-onboarding-plan/v1",
        "template": {"id": template["id"], "version": template["version"], "digest": digest(template)},
        "profile": template["profile"],
        "facts": facts,
        "missing_inputs": missing,
        "accepted_discovery_digest": discovery_digest if accept_discovery else None,
        "status": "ready_to_begin" if not missing else "needs_human_input",
        "authority_effect": "none; this plan prepares non-authoritative intake context only",
    }
    _validate("onboarding-plan.schema.json", result)
    return result


def apply_onboarding(root, template, answers, discovery=None, accept_discovery=False, template_dir=TEMPLATE_DIR):
    plan = plan_onboarding(template, answers, discovery, accept_discovery, template_dir)
    if plan["missing_inputs"]:
        raise ValueError("onboarding plan still needs human input")
    system_id = plan["facts"].get("system_id")
    if not system_id:
        raise ValueError("onboarding template must produce system_id")
    state = Path(root) / ".clses-v1"
    if state.exists():
        operator = GuidedOperator(root)
    else:
        operator = GuidedOperator.setup(
            root,
            system_id=system_id,
            purpose=plan["facts"].get("purpose", "Provide a reliable service"),
            beneficiary=(plan["facts"].get("beneficiaries") or ["users"])[0],
        )
    view = operator.begin(plan["profile"], {"facts": plan["facts"]})
    return {"plan": plan, "view": view}
