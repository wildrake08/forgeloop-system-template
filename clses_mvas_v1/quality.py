"""Composable, threshold-explicit software quality assessment."""
from __future__ import annotations

import argparse
import json
import operator
import time
from pathlib import Path

from jsonschema import Draft202012Validator

from .assurance import load_profile
from .store import digest


ROOT = Path(__file__).resolve().parent
PROFILE_DIR = ROOT / "quality_profiles"
SCHEMA_DIR = ROOT / "schemas"
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}


def _schema(name):
    return json.loads((SCHEMA_DIR / name).read_text())


def _validate(name, value):
    errors = sorted(Draft202012Validator(_schema(name)).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ValueError("normative " + name + " failure: " + errors[0].message)


def load_quality_profile(profile="software-quality", profile_dir=PROFILE_DIR, _stack=None):
    profile_dir = Path(profile_dir)
    path = Path(profile) if isinstance(profile, (str, Path)) and Path(profile).exists() else profile_dir / (str(profile) + ".json")
    value = json.loads(path.read_text())
    _validate("software-quality-profile.schema.json", value)
    stack = set() if _stack is None else set(_stack)
    if value["profile_id"] in stack:
        raise ValueError("cyclic software quality profile extension")
    stack.add(value["profile_id"])
    dimensions = []
    criteria = []
    lineage = []
    system_classes = []
    for parent in value["extends"]:
        composed = load_quality_profile(parent, profile_dir, stack)
        dimensions += composed["dimensions"]
        criteria += composed["criteria"]
        lineage += composed["lineage"]
        system_classes += composed["system_classes"]
    dimensions += value["dimensions"]
    criteria += value["criteria"]
    system_classes += value["system_classes"]
    lineage.append({"profile_id": value["profile_id"], "version": value["version"]})
    dimension_ids = [item["id"] for item in dimensions]
    criterion_ids = [item["id"] for item in criteria]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("duplicate quality dimension across composed profiles")
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("duplicate quality criterion across composed profiles")
    known_dimensions = set(dimension_ids)
    if any(item["dimension"] not in known_dimensions for item in criteria):
        raise ValueError("quality criterion references an unknown dimension")
    if any(item["applicability"] == "contextual" and not item["context_tags"] for item in criteria):
        raise ValueError("contextual quality criteria require context tags")
    return {
        "profile_id": value["profile_id"],
        "version": value["version"],
        "system_classes": list(dict.fromkeys(system_classes)),
        "dimensions": dimensions,
        "criteria": criteria,
        "lineage": lineage,
        "tradeoff_policy": value["tradeoff_policy"],
        "threshold_policy": value["threshold_policy"],
    }


def applicable_criteria(profile, context_tags):
    composed = load_quality_profile(profile) if not isinstance(profile, dict) else profile
    tags = set(context_tags)
    return {
        item["id"]
        for item in composed["criteria"]
        if item["applicability"] == "always" or bool(tags & set(item["context_tags"]))
    }


def affected_criteria(profile, change_kinds):
    composed = load_quality_profile(profile) if not isinstance(profile, dict) else profile
    kinds = set(change_kinds)
    return sorted(item["id"] for item in composed["criteria"] if kinds & set(item["change_triggers"]))


def validate_lifecycle_binding(quality_profile="software-quality", lifecycle_profile="software-quality"):
    quality = load_quality_profile(quality_profile)
    lifecycle = load_profile(lifecycle_profile)
    criteria = {item["id"]: item for item in quality["criteria"]}
    controls = {item["id"]: item for item in lifecycle["controls"] if item["id"] in criteria}
    errors = []
    if set(controls) != set(criteria):
        errors.append("lifecycle quality controls and quality criteria differ")
    for identifier in sorted(set(controls) & set(criteria)):
        control = controls[identifier]
        criterion = criteria[identifier]
        if control["evidence_types"] != [criterion["evidence_type"]]:
            errors.append(identifier + ": evidence type mismatch")
        if control["authority_role"] != criterion["authority_role"]:
            errors.append(identifier + ": authority role mismatch")
        if control["max_age_seconds"] != criterion["max_age_seconds"]:
            errors.append(identifier + ": evidence age mismatch")
    return errors


def assess_quality(assessment, profile="software-quality", now=None, profile_dir=PROFILE_DIR):
    now = int(time.time()) if now is None else int(now)
    try:
        composed = load_quality_profile(profile, profile_dir)
        _validate("quality-assessment.schema.json", assessment)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "checks": {"structure": False}, "errors": [str(exc)], "intrinsic": "nonconformant", "relational": "not_adequate"}
    criteria = {item["id"]: item for item in composed["criteria"]}
    dimensions = {item["id"] for item in composed["dimensions"]}
    decisions = assessment["criteria_decisions"]
    observations = assessment["observations"]
    tradeoffs = assessment["tradeoffs"]
    decision_index = {item["criterion_id"]: item for item in decisions}
    observation_index = {item["criterion_id"]: item for item in observations}
    tradeoff_index = {item["id"]: item for item in tradeoffs}
    required = applicable_criteria(composed, assessment["context_tags"])
    checks = {
        "profile_binding": assessment["profile"] == {"profile_id": composed["profile_id"], "version": composed["version"], "composed_digest": digest(composed)},
        "assessment_time": assessment["assessed_at"] <= now,
        "exact_decision_set": len(decision_index) == len(decisions) == len(criteria) and set(decision_index) == set(criteria),
        "unique_observations": len(observation_index) == len(observations),
        "unique_tradeoffs": len(tradeoff_index) == len(tradeoffs),
    }
    decision_valid = True
    evidence_valid = True
    passing = set()
    referenced_tradeoffs = set()
    for identifier, criterion in criteria.items():
        decision = decision_index.get(identifier)
        if decision is None:
            decision_valid = False
            continue
        expected_applicable = identifier in required
        if expected_applicable and decision["applicable"] is not True:
            decision_valid = False
        if decision["authority_role"] != criterion["authority_role"] or decision["decided_at"] > assessment["assessed_at"]:
            decision_valid = False
        referenced_tradeoffs.update(decision["tradeoff_refs"])
        observation = observation_index.get(identifier)
        if decision["applicable"]:
            threshold_valid = decision["operator"] == criterion["operator"] and decision["unit"] == criterion["unit"] and isinstance(decision["threshold"], (int, float))
            if not threshold_valid:
                decision_valid = False
            if observation is None:
                evidence_valid = False
                continue
            fresh = observation["observed_at"] <= assessment["assessed_at"] <= now <= observation["expires_at"] and observation["expires_at"] - observation["observed_at"] <= criterion["max_age_seconds"]
            bound = observation["metric"] == criterion["metric"] and observation["unit"] == criterion["unit"] and observation["environment_id"] == assessment["environment_id"]
            if fresh and bound and threshold_valid and OPS[criterion["operator"]](observation["value"], decision["threshold"]):
                passing.add(identifier)
            else:
                evidence_valid = False
        else:
            if observation is not None or decision["operator"] is not None or decision["threshold"] is not None or decision["unit"] is not None:
                decision_valid = False
    checks["applicability_and_thresholds"] = decision_valid
    checks["exact_observation_set"] = set(observation_index) == {identifier for identifier, decision in decision_index.items() if decision["applicable"]}
    checks["evidence_current_and_passing"] = evidence_valid and passing == {identifier for identifier, decision in decision_index.items() if decision["applicable"]}
    tradeoff_valid = referenced_tradeoffs == set(tradeoff_index)
    for item in tradeoffs:
        tradeoff_valid = tradeoff_valid and set(item["criterion_ids"]) <= set(criteria) and item["decided_at"] <= assessment["assessed_at"] < item["review_by"] and all(item["id"] in decision_index[criterion]["tradeoff_refs"] for criterion in item["criterion_ids"])
    checks["tradeoffs_governed"] = tradeoff_valid
    dimension_results = {}
    for dimension in dimensions:
        ids = {item["id"] for item in criteria.values() if item["dimension"] == dimension and decision_index.get(item["id"], {}).get("applicable")}
        dimension_results[dimension] = "not_applicable" if not ids else "pass" if ids <= passing else "fail"
    checks["all_dimensions_disposed"] = set(dimension_results) == dimensions and all(value in ("pass", "not_applicable") for value in dimension_results.values())
    valid = all(checks.values())
    errors = ["failed quality check: " + name for name, value in checks.items() if not value]
    return {
        "valid": valid,
        "checks": checks,
        "errors": errors,
        "intrinsic": "conformant" if valid else "nonconformant",
        "relational": "quality_criteria_satisfied_for_declared_context_environment_and_evidence_window" if valid else "not_adequate",
        "profile": composed["profile_id"],
        "system_id": assessment["system_id"],
        "environment_id": assessment["environment_id"],
        "required_criteria": sorted(required),
        "dimensions": dimension_results,
        "valid_until": min((item["expires_at"] for item in observations), default=0),
        "claim_boundary": "system-specific authority-declared thresholds, selected context tags, named environment, supplied observations, governed tradeoffs, and evidence expiry; not a universal quality certification",
    }


def main(default_profile="software-quality", prog="clses-quality"):
    parser = argparse.ArgumentParser(prog=prog)
    commands = parser.add_subparsers(dest="command", required=True)
    item = commands.add_parser("applicable")
    item.add_argument("--profile", default=default_profile)
    item.add_argument("--context-tag", action="append", default=[])
    item = commands.add_parser("affected")
    item.add_argument("--profile", default=default_profile)
    item.add_argument("--change-kind", action="append", required=True)
    item = commands.add_parser("assess")
    item.add_argument("assessment")
    item.add_argument("--profile", default=default_profile)
    item.add_argument("--profile-dir", default=str(PROFILE_DIR))
    args = parser.parse_args()
    if args.command == "applicable":
        result = {"criteria": sorted(applicable_criteria(load_quality_profile(args.profile), args.context_tag))}
    elif args.command == "affected":
        result = {"criteria": affected_criteria(load_quality_profile(args.profile), args.change_kind)}
    else:
        result = assess_quality(json.loads(Path(args.assessment).read_text()), args.profile, profile_dir=args.profile_dir)
    print(json.dumps(result, indent=2))
    return 0 if args.command != "assess" or result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
