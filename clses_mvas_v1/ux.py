"""Population-, journey-, and context-bound UX engineering assessment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .quality import PROFILE_DIR, affected_criteria, applicable_criteria, assess_quality, load_quality_profile


SCHEMA = Path(__file__).resolve().parent / "schemas" / "ux-assessment.schema.json"


def assess_ux(assessment, now=None, profile_dir=PROFILE_DIR):
    errors = sorted(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(assessment), key=lambda error: list(error.path))
    if errors:
        return {"valid": False, "checks": {"structure": False}, "errors": ["normative ux-assessment.schema.json failure: " + errors[0].message], "intrinsic": "nonconformant", "relational": "not_adequate"}

    quality_assessment = assessment["quality_assessment"]
    quality_result = assess_quality(quality_assessment, "ux-engineering", now=now, profile_dir=profile_dir)
    if not quality_result["valid"]:
        return {
            "valid": False,
            "checks": {"structure": True, "quality_assessment": False},
            "errors": ["nested quality assessment is nonconformant", *quality_result["errors"]],
            "intrinsic": "nonconformant",
            "relational": "not_adequate",
            "quality_result": quality_result,
        }
    profile = load_quality_profile("ux-engineering", profile_dir)
    criteria = {item["id"]: item for item in profile["criteria"] if item["id"].startswith("ux-")}
    observations = {item["criterion_id"]: item for item in quality_assessment["observations"]}
    decisions = {item["criterion_id"]: item for item in quality_assessment["criteria_decisions"]}
    scopes = assessment["criterion_scopes"]
    scope_index = {item["criterion_id"]: item for item in scopes}
    required_scopes = {identifier for identifier in criteria if decisions.get(identifier, {}).get("applicable")}
    context = assessment["ux_context"]
    populations = set(context["population_ids"])
    journeys = set(context["journey_ids"])
    operating_contexts = set(context["operating_context_ids"])
    instruments = set(context["instrument_ids"])

    checks = {
        "structure": True,
        "quality_assessment": quality_result["valid"],
        "ux_profile_binding": quality_assessment["profile"]["profile_id"] == "ux-engineering",
        "unique_scope_bindings": len(scope_index) == len(scopes),
        "exact_applicable_ux_scope_set": set(scope_index) == required_scopes,
    }
    binding_valid = True
    instrument_valid = True
    temporal_valid = assessment["research_ethics"]["approved_at"] <= quality_assessment["assessed_at"]
    for identifier, scope in scope_index.items():
        criterion = criteria.get(identifier)
        observation = observations.get(identifier)
        if criterion is None or observation is None:
            binding_valid = False
            continue
        binding_valid = binding_valid and set(scope["population_ids"]) <= populations
        binding_valid = binding_valid and set(scope["journey_ids"]) <= journeys
        binding_valid = binding_valid and set(scope["operating_context_ids"]) <= operating_contexts
        binding_valid = binding_valid and scope["evidence_digest"] == observation["evidence_digest"]
        if criterion["unit"] == "instrument_score":
            instrument_valid = instrument_valid and scope["instrument_id"] in instruments
        elif scope["instrument_id"] is not None:
            instrument_valid = instrument_valid and scope["instrument_id"] in instruments
    checks["evidence_scope_binding"] = binding_valid
    checks["declared_instrument_binding"] = instrument_valid
    checks["research_ethics_authorized_before_assessment"] = temporal_valid
    valid = all(checks.values())
    return {
        "valid": valid,
        "checks": checks,
        "errors": ["failed UX check: " + name for name, value in checks.items() if not value],
        "intrinsic": "conformant" if valid else "nonconformant",
        "relational": "ux_criteria_satisfied_for_declared_users_journeys_contexts_environment_instruments_and_evidence_window" if valid else "not_adequate",
        "profile": "ux-engineering",
        "system_id": quality_assessment["system_id"],
        "required_ux_criteria": sorted(required_scopes),
        "quality_result": quality_result,
        "claim_boundary": "declared user populations, critical journeys, operating contexts, environment, instruments, human-authorized thresholds, supplied evidence, research-ethics record, and evidence expiry; not universal usability or accessibility certification",
    }


def main():
    parser = argparse.ArgumentParser(prog="clses-ux")
    commands = parser.add_subparsers(dest="command", required=True)
    item = commands.add_parser("applicable")
    item.add_argument("--context-tag", action="append", default=[])
    item = commands.add_parser("affected")
    item.add_argument("--change-kind", action="append", required=True)
    item = commands.add_parser("assess")
    item.add_argument("assessment")
    item.add_argument("--profile-dir", default=str(PROFILE_DIR))
    args = parser.parse_args()
    if args.command == "applicable":
        result = {"criteria": sorted(applicable_criteria(load_quality_profile("ux-engineering"), args.context_tag))}
    elif args.command == "affected":
        result = {"criteria": affected_criteria(load_quality_profile("ux-engineering"), args.change_kind)}
    else:
        result = assess_ux(json.loads(Path(args.assessment).read_text()), profile_dir=args.profile_dir)
    print(json.dumps(result, indent=2))
    return 0 if args.command != "assess" or result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
