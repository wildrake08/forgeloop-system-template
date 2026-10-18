import copy
import time
import unittest

from clses_mvas_v1.assurance import load_profile
from clses_mvas_v1.quality import affected_criteria, applicable_criteria, assess_quality, load_quality_profile, validate_lifecycle_binding
from clses_mvas_v1.store import digest


class SoftwareQualityProfileTest(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time())
        self.profile = load_quality_profile()
        self.context = ["user_interface", "personal_data", "persistent_state", "external_dependency", "high_load"]
        self.assessment = self.make_assessment()

    def make_assessment(self):
        required = applicable_criteria(self.profile, self.context)
        decisions = []
        observations = []
        for criterion in self.profile["criteria"]:
            applies = criterion["id"] in required
            threshold = 1.0 if criterion["unit"] == "ratio" else 100
            if criterion["operator"] in ("<=", "<"):
                value = 0 if criterion["unit"] in ("ratio", "count") else 50
            else:
                value = threshold
            decisions.append({
                "criterion_id": criterion["id"], "applicable": applies,
                "rationale": "Required by declared context" if applies else "Context trigger is absent",
                "operator": criterion["operator"] if applies else None,
                "threshold": threshold if applies else None,
                "unit": criterion["unit"] if applies else None,
                "authority": "person-" + criterion["authority_role"],
                "authority_role": criterion["authority_role"], "decided_at": self.now - 20, "tradeoff_refs": [],
            })
            if applies:
                observations.append({
                    "criterion_id": criterion["id"], "metric": criterion["metric"], "unit": criterion["unit"], "value": value,
                    "observed_at": self.now - 10, "expires_at": self.now + 100, "evidence_digest": digest(criterion["id"]), "environment_id": "prod-coffee",
                })
        return {
            "format": "CLSES-quality-assessment/v1", "assessment_id": "qa-coffee-1", "system_id": "coffee-pos",
            "profile": {"profile_id": self.profile["profile_id"], "version": self.profile["version"], "composed_digest": digest(self.profile)},
            "context_tags": self.context, "environment_id": "prod-coffee", "criteria_decisions": decisions,
            "observations": observations, "tradeoffs": [], "assessed_at": self.now,
        }

    def result(self, assessment=None):
        return assess_quality(assessment or self.assessment, now=self.now)

    def test_profile_covers_nine_dimensions_and_eighteen_criteria(self):
        self.assertEqual(len(self.profile["dimensions"]), 9)
        self.assertEqual(len(self.profile["criteria"]), 18)
        self.assertEqual({item["dimension"] for item in self.profile["criteria"]}, {item["id"] for item in self.profile["dimensions"]})

    def test_quality_profile_is_bound_to_lifecycle_controls(self):
        self.assertEqual(validate_lifecycle_binding(), [])

    def test_point_of_sale_and_saas_compose_quality_profile(self):
        for profile_id in ("point-of-sale", "saas"):
            profile = load_profile(profile_id)
            controls = {item["id"] for item in profile["controls"]}
            self.assertTrue({item["id"] for item in self.profile["criteria"]} <= controls)
            self.assertIn({"profile_id": "software-quality", "version": "1.0.0"}, profile["lineage"])

    def test_complete_quality_assessment_passes(self):
        result = self.result()
        self.assertTrue(result["valid"])
        self.assertEqual(result["intrinsic"], "conformant")
        self.assertEqual(result["dimensions"]["safety"], "not_applicable")

    def test_profile_never_supplies_consequential_threshold_defaults(self):
        self.assertIn("no consequential threshold defaults", self.profile["threshold_policy"])
        self.assertTrue(all("threshold" not in item for item in self.profile["criteria"]))

    def test_required_criterion_cannot_be_excluded(self):
        value = copy.deepcopy(self.assessment)
        decision = next(item for item in value["criteria_decisions"] if item["criterion_id"] == "quality-functional-completeness")
        decision.update({"applicable": False, "operator": None, "threshold": None, "unit": None})
        value["observations"] = [item for item in value["observations"] if item["criterion_id"] != decision["criterion_id"]]
        self.assertFalse(self.result(value)["checks"]["applicability_and_thresholds"])

    def test_missing_authority_threshold_fails(self):
        value = copy.deepcopy(self.assessment)
        decision = next(item for item in value["criteria_decisions"] if item["applicable"])
        decision["threshold"] = None
        self.assertFalse(self.result(value)["checks"]["applicability_and_thresholds"])

    def test_wrong_unit_and_failing_measurement_fail(self):
        value = copy.deepcopy(self.assessment)
        observation = next(item for item in value["observations"] if item["criterion_id"] == "quality-response-time")
        observation["unit"] = "seconds"
        self.assertFalse(self.result(value)["checks"]["evidence_current_and_passing"])
        value = copy.deepcopy(self.assessment)
        observation = next(item for item in value["observations"] if item["criterion_id"] == "quality-response-time")
        observation["value"] = 1000
        self.assertFalse(self.result(value)["checks"]["evidence_current_and_passing"])
        value = copy.deepcopy(self.assessment)
        extra = copy.deepcopy(value["observations"][0]);extra["criterion_id"] = "unknown-quality-criterion";value["observations"].append(extra)
        self.assertFalse(self.result(value)["checks"]["exact_observation_set"])

    def test_stale_quality_evidence_fails(self):
        value = copy.deepcopy(self.assessment)
        value["observations"][0]["expires_at"] = self.now - 1
        self.assertFalse(self.result(value)["checks"]["evidence_current_and_passing"])

    def test_tradeoff_must_be_bound_and_review_dated(self):
        value = copy.deepcopy(self.assessment)
        value["tradeoffs"] = [{"id": "t1", "criterion_ids": ["quality-response-time"], "decision": "Prefer offline reliability", "rationale": "Connectivity is intermittent", "authority": "quality-board", "decided_at": self.now - 1, "review_by": self.now + 100}]
        self.assertFalse(self.result(value)["checks"]["tradeoffs_governed"])
        decision = next(item for item in value["criteria_decisions"] if item["criterion_id"] == "quality-response-time")
        decision["tradeoff_refs"] = ["t1"]
        self.assertTrue(self.result(value)["checks"]["tradeoffs_governed"])

    def test_context_selects_only_applicable_optional_criteria(self):
        required = applicable_criteria(self.profile, ["safety_relevant"])
        self.assertIn("quality-fail-safe", required)
        self.assertIn("quality-hazard-control", required)
        self.assertNotIn("quality-confidentiality", required)
        self.assertIn("quality-integrity", required)

    def test_change_triggers_targeted_reassessment(self):
        affected = affected_criteria(self.profile, ["dependency"])
        self.assertIn("quality-response-time", affected)
        self.assertIn("quality-integrity", affected)
        self.assertIn("quality-replaceability", affected)
        self.assertNotIn("quality-operability", affected)


if __name__ == "__main__":
    unittest.main()
