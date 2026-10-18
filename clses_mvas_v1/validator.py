"""Normative CLSES-MVAS v0.3.1 structural and cross-artifact validator.

This establishes internal consistency only. It does not authenticate actors,
attest external provenance, or promote synthetic evidence to relational adequacy.
"""
from __future__ import annotations

import argparse
import json
import operator
import sys
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

SOURCE_BASE = Path(__file__).resolve().parent.parent
PACKAGE_BASE = Path(__file__).resolve().parent
BASE = SOURCE_BASE if (SOURCE_BASE / "schemas" / "manifest.schema.json").exists() else PACKAGE_BASE
TYPES = tuple(f"A{i}" for i in range(1, 9))
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
       "==": operator.eq, "!=": operator.ne}


def _load_schema(name):
    return json.loads((BASE / "schemas" / name).read_text())


def check_schemas():
    """Return meta-schema errors for every normative schema."""
    errors = []
    names = ["manifest.schema.json", "lifecycle-profile.schema.json", "adapter-manifest.schema.json", "adapter-request.schema.json", "adapter-result.schema.json", "production-observation.schema.json", "assurance-dossier.schema.json", "minimal-intake-state.schema.json", "minimal-viable-baseline.schema.json", "onboarding-template.schema.json", "onboarding-plan.schema.json", "environment-discovery.schema.json", "guided-operator-state.schema.json", "authorization-request-packet.schema.json", "software-quality-profile.schema.json", "quality-assessment.schema.json", "ux-assessment.schema.json", *[f"artifacts/{kind}.schema.json" for kind in TYPES]]
    for name in names:
        try:
            Draft202012Validator.check_schema(_load_schema(name))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    return sorted(errors)


def _schema_errors(instance, schema, prefix):
    result = []
    for failure in Draft202012Validator(schema).iter_errors(instance):
        path = "/".join(str(part) for part in failure.absolute_path)
        result.append(f"{prefix}{('/' + path) if path else ''}: {failure.message}")
    return result


def validate(manifest):
    """Validate one complete manifest against schemas and all v0.3.1 invariants."""
    errors = []
    errors.extend(_schema_errors(manifest, _load_schema("manifest.schema.json"), "manifest"))
    if errors:
        return sorted(set(errors))

    artifacts = manifest["artifacts"]
    for pos, artifact in enumerate(artifacts):
        errors.extend(_schema_errors(
            artifact["payload"], _load_schema(f"artifacts/{artifact['type']}.schema.json"),
            f"artifact[{pos}] {artifact['id']}"
        ))
        if artifact["subject"] != manifest["system_id"]:
            errors.append(f"{artifact['id']}: subject differs from manifest system_id")
    if errors:
        return sorted(set(errors))

    index = {}
    histories = defaultdict(list)
    for artifact in artifacts:
        key = (artifact["id"], artifact["version"])
        if key in index:
            errors.append(f"duplicate revision {artifact['id']}@{artifact['version']}")
        index[key] = artifact
        histories[artifact["id"]].append(artifact)
    if errors:
        return sorted(set(errors))

    def ref_key(ref):
        return ref["id"], ref["version"]

    def edge_keys(artifact):
        return {ref_key(ref) for ref in artifact["references"]}

    def resolve(ref, owner, expected=None, require_edge=None):
        target = index.get(ref_key(ref))
        if target is None:
            errors.append(f"{owner}: dangling reference {ref['id']}@{ref['version']}")
            return None
        if expected and target["type"] not in expected:
            errors.append(f"{owner}: {ref['id']}@{ref['version']} must be {'/'.join(expected)}, got {target['type']}")
        if require_edge is not None and ref_key(ref) not in edge_keys(require_edge):
            errors.append(f"{owner}: typed reference {ref['id']}@{ref['version']} missing from references")
        return target

    # Identity, immutable type/subject, contiguous histories, and exact supersession.
    active = {}
    for artifact_id, revisions in histories.items():
        revisions.sort(key=lambda item: item["version"])
        active[artifact_id] = revisions[-1]
        versions = [item["version"] for item in revisions]
        if versions != list(range(1, versions[-1] + 1)):
            errors.append(f"{artifact_id}: revisions must be contiguous from version 1")
        if len({item["type"] for item in revisions}) != 1:
            errors.append(f"{artifact_id}: artifact type changes across revisions")
        if len({item["subject"] for item in revisions}) != 1:
            errors.append(f"{artifact_id}: subject changes across revisions")
        for position, revision in enumerate(revisions):
            expected = None if position == 0 else {"id": artifact_id, "version": revisions[position - 1]["version"]}
            if revision["supersedes"] != expected:
                errors.append(f"{artifact_id}@{revision['version']}: invalid supersedes link")
            if expected and ref_key(expected) not in edge_keys(revision):
                errors.append(f"{artifact_id}@{revision['version']}: superseded revision missing from references")

    active_by_type = {kind: [item for item in active.values() if item["type"] == kind] for kind in TYPES}
    for kind in TYPES:
        if not active_by_type[kind]:
            errors.append(f"complete manifest requires an active {kind} artifact")
    if len(active_by_type["A1"]) != 1:
        errors.append("complete manifest requires exactly one active A1 artifact")

    # Reference direction is part of ownership. Every envelope graph must be acyclic.
    allowed_targets = {
        "A1": {"A1"}, "A2": {"A1", "A2"}, "A3": {"A2", "A3"},
        "A4": {"A3", "A4", "A7", "A8"}, "A5": {"A3", "A4", "A5", "A8"},
        "A6": {"A1", "A2", "A6"}, "A7": {"A5", "A6", "A7"},
        "A8": set(TYPES),
    }
    graph = {key: [] for key in index}
    for key, artifact in index.items():
        for ref in artifact["references"]:
            target = resolve(ref, f"{artifact['id']}@{artifact['version']}")
            if target:
                graph[key].append(ref_key(ref))
                if target["type"] not in allowed_targets[artifact["type"]]:
                    errors.append(f"{artifact['id']}@{artifact['version']}: impermissible {artifact['type']}->{target['type']} reference")
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            errors.append("cross-artifact reference graph contains a cycle")
            return
        if key in visited:
            return
        visiting.add(key)
        for child in graph[key]:
            visit(child)
        visiting.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)

    purpose = active_by_type["A1"][0] if len(active_by_type["A1"]) == 1 else None
    if purpose and purpose["payload"]["horizon"]["end"] < purpose["payload"]["horizon"]["start"]:
        errors.append(f"{purpose['id']}: outcome horizon is inverted")

    def is_active(target):
        return bool(target and active.get(target["id"]) is target)

    def require_active(owner, ref, expected):
        target = resolve(ref, owner["id"], expected, owner)
        if target and not is_active(target):
            errors.append(f"{owner['id']}: operative reference {target['id']}@{target['version']} is stale")
        return target

    # Lifecycle histories.
    work_transitions = {
        "proposed": {"proposed", "authorized", "withdrawn"},
        "authorized": {"authorized", "executing", "withdrawn"},
        "executing": {"executing", "executed", "failed"},
        "executed": {"executed"}, "failed": {"failed", "authorized"}, "withdrawn": {"withdrawn"},
    }
    decision_transitions = {
        "proposed": {"proposed", "approved", "denied"}, "approved": {"approved", "revoked"},
        "denied": {"denied"}, "revoked": {"revoked"}, "open": {"open"},
        "failed": {"failed"}, "closed_verified": {"closed_verified"},
        "closed_exception": {"closed_exception"},
    }
    for revisions in histories.values():
        for before, after in zip(revisions, revisions[1:]):
            if before["type"] == "A4":
                for field in ("work_id", "assigned_actor", "design_ref"):
                    if before["payload"][field] != after["payload"][field]:
                        errors.append(f"{after['id']}: {field} changes across work revisions")
                old, new = before["payload"]["work_state"], after["payload"]["work_state"]
                if new not in work_transitions[old]:
                    errors.append(f"{after['id']}: invalid work transition {old}->{new}")
                if after["payload"]["state_changed_at"] < before["payload"]["state_changed_at"]:
                    errors.append(f"{after['id']}: work transition time moves backward")
            if before["type"] == "A8":
                for field in ("decision_kind", "actor", "authorized_actor", "scope", "authority_source"):
                    if before["payload"][field] != after["payload"][field]:
                        errors.append(f"{after['id']}: {field} changes across decision revisions")
                old, new = before["payload"]["decision"], after["payload"]["decision"]
                if new not in decision_transitions[old]:
                    errors.append(f"{after['id']}: invalid decision transition {old}->{new}")
                if after["payload"]["decided_at"] < before["payload"]["decided_at"]:
                    errors.append(f"{after['id']}: decision time moves backward")
            if before["type"] == "A5" and before["payload"]["deployment"] and not after["payload"]["deployment"]:
                errors.append(f"{after['id']}: deployment record cannot disappear")
        if revisions[0]["type"] == "A7" and len(revisions) > 1:
            errors.append(f"{revisions[0]['id']}: observations are append-only and cannot be revised")

    def authorization_valid(grant, kind, scope, effective_at, authorized_actor=None):
        if not grant or grant["type"] != "A8":
            return False
        payload = grant["payload"]
        if not (payload["decision_kind"] == kind and payload["decision"] == "approved"
                and payload["scope"] in (scope, "*")
                and payload["decided_at"] <= effective_at <= payload["valid_until"]):
            return False
        if authorized_actor is not None and payload.get("authorized_actor") != authorized_actor:
            return False
        for revocation in active_by_type["A8"]:
            rp = revocation["payload"]
            if (rp["decision_kind"] == "revocation" and rp["decision"] == "approved"
                    and rp["target_ref"] and ref_key(rp["target_ref"]) == (grant["id"], grant["version"])
                    and rp["decided_at"] <= effective_at):
                return False
        return True

    criteria = {}
    observations_by_method = defaultdict(list)
    observations_by_target = defaultdict(list)
    for artifact in active.values():
        payload, kind = artifact["payload"], artifact["type"]
        if kind in ("A1", "A2"):
            records = payload["outcomes"] if kind == "A1" else payload["requirements"]
            keys = [item["key"] for item in records]
            if len(keys) != len(set(keys)):
                errors.append(f"{artifact['id']}: duplicate criterion key")
            for item in records:
                criteria[(artifact["id"], artifact["version"], item["key"])] = item

    # Active ownership, authorization, evidence, and closure rules.
    for artifact in active.values():
        payload, kind = artifact["payload"], artifact["type"]
        if kind == "A2":
            require_active(artifact, payload["purpose_ref"], ("A1",))
        elif kind == "A3":
            for ref in payload["requirements_refs"]:
                require_active(artifact, ref, ("A2",))
        elif kind == "A4":
            require_active(artifact, payload["design_ref"], ("A3",))
            state = payload["work_state"]
            if payload["state_changed_at"] > manifest["assessed_at"]:
                errors.append(f"{artifact['id']}: work state is dated after assessment")
            if state in ("authorized", "executing", "executed", "failed"):
                ref = payload["authorization_ref"]
                grant = resolve(ref, artifact["id"], ("A8",), artifact) if ref else None
                if not authorization_valid(grant, "engineering_authorization", payload["work_id"],
                                           payload["state_changed_at"], payload["assigned_actor"]):
                    errors.append(f"{artifact['id']}: invalid, expired, revoked, or wrongly scoped engineering authorization")
            if state == "executed":
                for ref in payload["execution_evidence_refs"]:
                    evidence = resolve(ref, artifact["id"], ("A7",), artifact)
                    if evidence and evidence["payload"]["kind"] != "execution":
                        errors.append(f"{artifact['id']}: execution evidence has wrong kind")
        elif kind == "A5":
            require_active(artifact, payload["design_ref"], ("A3",))
            deployment = payload["deployment"]
            if deployment:
                ref = deployment["production_authorization_ref"]
                grant = resolve(ref, artifact["id"], ("A8",), artifact)
                if not authorization_valid(grant, "production_authorization", deployment["release_id"], deployment["deployed_at"]):
                    errors.append(f"{artifact['id']}: deployment lacks an exact valid production authorization")
        elif kind == "A6":
            criterion_artifact = require_active(artifact, payload["criterion_ref"], ("A1", "A2"))
            criterion = criteria.get((*ref_key(payload["criterion_ref"]), payload["criterion_key"]))
            if criterion_artifact and criterion is None:
                errors.append(f"{artifact['id']}: criterion key does not exist")
            elif criterion:
                if criterion["variable"] != payload["bindings"]["variable"]:
                    errors.append(f"{artifact['id']}: criterion variable binding differs")
                if criterion["unit"] != payload["bindings"]["measurement_unit"]:
                    errors.append(f"{artifact['id']}: criterion measurement unit differs")
        elif kind == "A7":
            target = require_active(artifact, payload["target_ref"], ("A5",))
            method = require_active(artifact, payload["method_ref"], ("A6",))
            if payload["observed_at"] > manifest["assessed_at"]:
                errors.append(f"{artifact['id']}: observation is in the future")
            if purpose:
                horizon = purpose["payload"]["horizon"]
                if not horizon["start"] <= payload["observed_at"] <= horizon["end"]:
                    errors.append(f"{artifact['id']}: observation lies outside purpose horizon")
            if not set(payload["source_ids"]).issubset(payload["source_provenance"]):
                errors.append(f"{artifact['id']}: source provenance is incomplete")
            if set(payload["measurements"]) != set(payload["measurement_units"]):
                errors.append(f"{artifact['id']}: measurement and unit keys differ")
            if method:
                mp = method["payload"]
                key = mp["bindings"]["measurement_key"]
                if key not in payload["measurements"]:
                    errors.append(f"{artifact['id']}: required measurement {key} is missing")
                elif payload["measurement_units"].get(key) != mp["bindings"]["measurement_unit"]:
                    errors.append(f"{artifact['id']}: measurement unit does not match method")
                if len(payload["source_ids"]) < mp["minimum_sources"]:
                    errors.append(f"{artifact['id']}: insufficient declared sources")
                if payload["coverage"] < mp["min_coverage"]:
                    errors.append(f"{artifact['id']}: insufficient coverage")
                if manifest["assessed_at"] - payload["observed_at"] > mp["max_age"]:
                    errors.append(f"{artifact['id']}: evidence is stale")
                observations_by_method[(method["id"], method["version"])].append(artifact)
            if target:
                observations_by_target[(target["id"], target["version"])].append(artifact)
        elif kind == "A8":
            if payload["decided_at"] > manifest["assessed_at"] or payload["valid_until"] < payload["decided_at"]:
                errors.append(f"{artifact['id']}: invalid decision time window")
            for ref in payload["basis_refs"]:
                resolve(ref, artifact["id"], ("A7",), artifact)
            target = None
            if payload["target_ref"]:
                expected = ("A8",) if payload["decision_kind"] in ("closure", "response", "risk_acceptance", "revocation") else TYPES
                target = resolve(payload["target_ref"], artifact["id"], expected, artifact)
            if payload["decision_kind"] == "closure":
                if not target or target["payload"]["decision_kind"] != "finding":
                    errors.append(f"{artifact['id']}: closure target is not a finding")
                if payload["decision"] == "closed_verified":
                    for ref in payload["basis_refs"]:
                        evidence = index.get(ref_key(ref))
                        if evidence and not _evidence_passes(evidence, index, payload["decided_at"]):
                            errors.append(f"{artifact['id']}: basis evidence does not satisfy its criterion")
                        if evidence and target and evidence["payload"]["observed_at"] < target["payload"]["decided_at"]:
                            errors.append(f"{artifact['id']}: basis evidence predates the finding")
                        if evidence and evidence["payload"]["observed_at"] > payload["decided_at"]:
                            errors.append(f"{artifact['id']}: basis evidence follows closure")
            if payload["decision_kind"] == "revocation":
                if not target or target["payload"]["decision_kind"] not in ("engineering_authorization", "production_authorization"):
                    errors.append(f"{artifact['id']}: revocation target is not an authorization")

    # Complete trace and evaluation coverage for active declarations.
    active_a2_keys = {(item["id"], item["version"]) for item in active_by_type["A2"]}
    design_coverage = {ref_key(ref) for design in active_by_type["A3"] for ref in design["payload"]["requirements_refs"]}
    if active_a2_keys - design_coverage:
        errors.append("active A2 requirements are not fully owned by active A3 design")
    method_coverage = {
        (*ref_key(method["payload"]["criterion_ref"]), method["payload"]["criterion_key"])
        for method in active_by_type["A6"]
    }
    missing_criteria = set(criteria) - method_coverage
    if missing_criteria:
        labels = ", ".join(f"{a}@{v}:{key}" for a, v, key in sorted(missing_criteria))
        errors.append(f"declared predicates lack A6 evaluation mappings: {labels}")
    for method in active_by_type["A6"]:
        if (method["id"], method["version"]) not in observations_by_method:
            errors.append(f"{method['id']}: active evaluation method has no active A7 observation")
    for implementation in active_by_type["A5"]:
        key = (implementation["id"], implementation["version"])
        if implementation["payload"]["deployment"] and key not in observations_by_target:
            errors.append(f"{implementation['id']}: deployed implementation has no active A7 observation")

    # Multiple active grants for the same authority domain and scope are ambiguous.
    grants = defaultdict(list)
    for decision in active_by_type["A8"]:
        payload = decision["payload"]
        if payload["decision_kind"] in ("engineering_authorization", "production_authorization") and payload["decision"] == "approved":
            grants[(payload["decision_kind"], payload["scope"])].append(decision)
    for (kind, scope), values in grants.items():
        if len(values) > 1:
            errors.append(f"conflicting active {kind} grants for scope {scope}")

    return sorted(set(errors))


def _evidence_passes(evidence, index, at_time):
    payload = evidence["payload"]
    method = index.get((payload["method_ref"]["id"], payload["method_ref"]["version"]))
    if not method or method["type"] != "A6":
        return False
    mp = method["payload"]
    criterion_artifact = index.get((mp["criterion_ref"]["id"], mp["criterion_ref"]["version"]))
    if not criterion_artifact or criterion_artifact["type"] not in ("A1", "A2"):
        return False
    records = criterion_artifact["payload"]["outcomes"] if criterion_artifact["type"] == "A1" else criterion_artifact["payload"]["requirements"]
    criterion = next((item for item in records if item["key"] == mp["criterion_key"]), None)
    key = mp["bindings"]["measurement_key"]
    value = payload["measurements"].get(key)
    return bool(
        criterion is not None and value is not None
        and OPS[criterion["op"]](value, criterion["threshold"])
        and payload["measurement_units"].get(key) == criterion["unit"]
        and payload["coverage"] >= mp["min_coverage"]
        and len(payload["source_ids"]) >= mp["minimum_sources"]
        and 0 <= at_time - payload["observed_at"] <= mp["max_age"]
    )


def assess(manifest):
    errors = validate(manifest)
    return {
        "intrinsic": "nonconformant" if errors else "conformant_to_v0.3.1_rules",
        "artifact_level": "fail" if errors else "pass",
        "system_level": "fail" if errors else "pass",
        "relational": "indeterminate",
        "errors": errors,
        "qualification": (
            "Internal schema and graph consistency is not authenticated external grounding, "
            "causal effectiveness, operational resilience, or sustained outcome evidence."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--assess", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    result = assess(manifest)
    print(json.dumps(result if args.assess else {"errors": result["errors"], "valid": not result["errors"]}, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    sys.exit(main())
