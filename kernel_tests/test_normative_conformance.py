import copy
import json
import unittest
from pathlib import Path

from clses_mvas_v1.validator import assess, check_schemas, validate

ROOT = Path(__file__).resolve().parents[1]


class NormativeConformanceTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "examples" / "synthetic-valid.json").read_text())

    def artifact(self, artifact_id):
        return next(item for item in self.manifest["artifacts"] if item["id"] == artifact_id)

    def rejected(self, contains=None):
        failures = validate(self.manifest)
        self.assertTrue(failures)
        if contains:
            self.assertTrue(any(contains in failure for failure in failures), failures)

    def add_work_revision(self, state, changed_at=81):
        previous = self.artifact("work")
        revision = copy.deepcopy(previous)
        revision["version"] = 2
        revision["supersedes"] = {"id": "work", "version": 1}
        revision["references"].append({"id": "work", "version": 1})
        revision["payload"]["work_state"] = state
        revision["payload"]["state_changed_at"] = changed_at
        self.manifest["artifacts"].append(revision)
        return revision

    def add_verified_closure(self):
        finding = {
            "id": "finding", "version": 1, "type": "A8", "subject": "demo",
            "payload": {
                "decision_kind": "finding", "actor": "assessor", "authorized_actor": None,
                "scope": "correctness", "decision": "open", "decided_at": 110,
                "basis_refs": [], "target_ref": {"id": "implementation", "version": 1},
                "authority_source": "quality-policy", "valid_until": 900,
            },
            "references": [{"id": "implementation", "version": 1}], "supersedes": None,
        }
        closure = {
            "id": "closure", "version": 1, "type": "A8", "subject": "demo",
            "payload": {
                "decision_kind": "closure", "actor": "assessor", "authorized_actor": None,
                "scope": "correctness", "decision": "closed_verified", "decided_at": 125,
                "basis_refs": [{"id": "observation", "version": 1}],
                "target_ref": {"id": "finding", "version": 1},
                "authority_source": "quality-policy", "valid_until": 900,
            },
            "references": [
                {"id": "finding", "version": 1},
                {"id": "observation", "version": 1},
            ],
            "supersedes": None,
        }
        self.manifest["artifacts"].extend([finding, closure])

    def test_all_normative_json_schemas_are_meta_schema_valid(self):
        self.assertEqual(check_schemas(), [])

    def test_complete_manifest_passes_both_consistency_levels(self):
        result = assess(self.manifest)
        self.assertEqual(result["artifact_level"], "pass")
        self.assertEqual(result["system_level"], "pass")
        self.assertEqual(result["relational"], "indeterminate")

    def test_valid_work_transition_history(self):
        self.add_work_revision("executing")
        self.assertEqual(validate(self.manifest), [])

    def test_verified_closure_with_passing_post_finding_evidence(self):
        self.add_verified_closure()
        self.assertEqual(validate(self.manifest), [])

    def test_every_artifact_type_is_required(self):
        self.manifest["artifacts"] = [item for item in self.manifest["artifacts"] if item["type"] != "A7"]
        self.rejected("requires an active A7")

    def test_predicate_coverage_is_complete(self):
        self.manifest["artifacts"] = [item for item in self.manifest["artifacts"] if item["id"] not in ("purpose-method", "purpose-observation")]
        self.rejected("lack A6 evaluation mappings")

    def test_each_method_requires_observation(self):
        self.manifest["artifacts"] = [item for item in self.manifest["artifacts"] if item["id"] != "purpose-observation"]
        self.rejected("has no active A7 observation")

    def test_typed_reference_must_be_envelope_edge(self):
        self.artifact("requirements")["references"] = []
        self.rejected("missing from references")

    def test_measurement_unit_must_match_criterion(self):
        self.artifact("observation")["payload"]["measurement_units"]["score"] = "percent"
        self.rejected("measurement unit")

    def test_measurement_and_unit_key_sets_must_match(self):
        self.artifact("observation")["payload"]["measurement_units"]["extra"] = "ratio"
        self.rejected("measurement and unit keys differ")

    def test_stale_operative_revision_is_rejected(self):
        design = self.artifact("design")
        revision = copy.deepcopy(design)
        revision["version"] = 2
        revision["supersedes"] = {"id": "design", "version": 1}
        revision["references"].append({"id": "design", "version": 1})
        self.manifest["artifacts"].append(revision)
        self.rejected("operative reference design@1 is stale")

    def test_revision_gap_is_rejected(self):
        work = self.add_work_revision("executing")
        work["version"] = 3
        work["supersedes"] = {"id": "work", "version": 1}
        self.rejected("contiguous")

    def test_wrong_supersedes_link_is_rejected(self):
        work = self.add_work_revision("executing")
        work["supersedes"] = {"id": "design", "version": 1}
        self.rejected("invalid supersedes link")

    def test_invalid_work_transition_is_rejected(self):
        self.add_work_revision("failed")
        self.rejected("invalid work transition authorized->failed")

    def test_work_actor_cannot_change_across_revisions(self):
        work = self.add_work_revision("executing")
        work["payload"]["assigned_actor"] = "different-agent"
        self.rejected("assigned_actor changes")

    def test_engineering_grant_authorized_actor_must_match(self):
        self.artifact("workgrant")["payload"]["authorized_actor"] = "other-agent"
        self.rejected("engineering authorization")

    def test_expired_engineering_grant_is_rejected_at_transition_time(self):
        self.artifact("workgrant")["payload"]["valid_until"] = 60
        self.rejected("engineering authorization")

    def test_revoked_engineering_grant_is_rejected(self):
        revocation = {
            "id": "revoke-work", "version": 1, "type": "A8", "subject": "demo",
            "payload": {
                "decision_kind": "revocation", "actor": "owner", "authorized_actor": None,
                "scope": "w1", "decision": "approved", "decided_at": 70,
                "basis_refs": [], "target_ref": {"id": "workgrant", "version": 1},
                "authority_source": "policy", "valid_until": 900,
            },
            "references": [{"id": "workgrant", "version": 1}], "supersedes": None,
        }
        self.manifest["artifacts"].append(revocation)
        self.rejected("engineering authorization")

    def test_production_grant_cannot_substitute_engineering_grant(self):
        work = self.artifact("work")
        work["payload"]["authorization_ref"] = {"id": "prodgrant", "version": 1}
        self.rejected("engineering authorization")

    def test_engineering_grant_cannot_substitute_production_grant(self):
        deployment = self.artifact("implementation")["payload"]["deployment"]
        deployment["production_authorization_ref"] = {"id": "workgrant", "version": 1}
        self.rejected("production authorization")

    def test_conflicting_grants_are_rejected(self):
        duplicate = copy.deepcopy(self.artifact("prodgrant"))
        duplicate["id"] = "prodgrant-two"
        self.manifest["artifacts"].append(duplicate)
        self.rejected("conflicting active production_authorization")

    def test_future_work_state_is_rejected(self):
        self.artifact("work")["payload"]["state_changed_at"] = 131
        self.rejected("dated after assessment")

    def test_failed_evidence_cannot_close_finding(self):
        self.add_verified_closure()
        self.artifact("observation")["payload"]["measurements"]["score"] = 0.5
        self.rejected("does not satisfy its criterion")

    def test_pre_finding_evidence_cannot_close_finding(self):
        self.add_verified_closure()
        self.artifact("finding")["payload"]["decided_at"] = 121
        self.rejected("predates the finding")

    def test_post_closure_evidence_is_rejected(self):
        self.add_verified_closure()
        self.artifact("closure")["payload"]["decided_at"] = 115
        self.rejected("follows closure")

    def test_observation_revisions_are_forbidden(self):
        observation = copy.deepcopy(self.artifact("observation"))
        observation["version"] = 2
        observation["supersedes"] = {"id": "observation", "version": 1}
        observation["references"].append({"id": "observation", "version": 1})
        self.manifest["artifacts"].append(observation)
        self.rejected("append-only")


if __name__ == "__main__":
    unittest.main()
