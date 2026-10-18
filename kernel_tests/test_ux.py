import copy
import time
import unittest

from clses_mvas_v1.assurance import load_profile
from clses_mvas_v1.quality import applicable_criteria, load_quality_profile, validate_lifecycle_binding
from clses_mvas_v1.store import digest
from clses_mvas_v1.ux import assess_ux


class UxEngineeringProfileTest(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time())
        self.profile = load_quality_profile("ux-engineering")
        self.context_tags = [
            "user_interface", "public_facing", "production_users", "instrumented_experience",
            "frequent_use", "localized", "ai_mediated", "persistent_state", "external_dependency",
        ]
        self.assessment = self.make_assessment()

    def make_assessment(self):
        required = applicable_criteria(self.profile, self.context_tags)
        decisions = []
        observations = []
        scopes = []
        for criterion in self.profile["criteria"]:
            applies = criterion["id"] in required
            threshold = 1.0 if criterion["unit"] == "ratio" else 100
            value = 0 if criterion["operator"] in ("<=", "<") else threshold
            decisions.append({
                "criterion_id": criterion["id"], "applicable": applies,
                "rationale": "Required by declared UX context" if applies else "Context trigger is absent",
                "operator": criterion["operator"] if applies else None,
                "threshold": threshold if applies else None,
                "unit": criterion["unit"] if applies else None,
                "authority": "person-" + criterion["authority_role"],
                "authority_role": criterion["authority_role"], "decided_at": self.now - 20, "tradeoff_refs": [],
            })
            if applies:
                evidence_digest = digest("evidence-" + criterion["id"])
                observations.append({
                    "criterion_id": criterion["id"], "metric": criterion["metric"], "unit": criterion["unit"],
                    "value": value, "observed_at": self.now - 10, "expires_at": self.now + 100,
                    "evidence_digest": evidence_digest, "environment_id": "coffee-cart-production",
                })
                if criterion["id"].startswith("ux-"):
                    scopes.append({
                        "criterion_id": criterion["id"], "population_ids": ["barista", "manager"],
                        "journey_ids": ["take-order", "refund"], "operating_context_ids": ["busy-cart"],
                        "instrument_id": "ux-score-v1" if criterion["unit"] == "instrument_score" else None,
                        "sample_size": 12, "evidence_digest": evidence_digest,
                    })
        quality = {
            "format": "CLSES-quality-assessment/v1", "assessment_id": "ux-quality-coffee-1", "system_id": "coffee-pos",
            "profile": {"profile_id": self.profile["profile_id"], "version": self.profile["version"], "composed_digest": digest(self.profile)},
            "context_tags": self.context_tags, "environment_id": "coffee-cart-production",
            "criteria_decisions": decisions, "observations": observations, "tradeoffs": [], "assessed_at": self.now,
        }
        return {
            "format": "CLSES-ux-assessment/v1", "quality_assessment": quality,
            "ux_context": {"population_ids": ["barista", "manager"], "journey_ids": ["take-order", "refund"], "operating_context_ids": ["busy-cart"], "instrument_ids": ["ux-score-v1"]},
            "criterion_scopes": scopes,
            "research_ethics": {"consent_basis": "informed participant consent", "privacy_review_ref": "privacy-review-17", "recruitment_limitations": "single-city pilot; reassess before expansion", "approved_by": "human-research-authority", "approved_at": self.now - 30},
        }

    def result(self, assessment=None):
        return assess_ux(assessment or self.assessment, now=self.now)

    def test_profile_composes_software_quality_and_ux(self):
        self.assertEqual(len(self.profile["dimensions"]), 19)
        self.assertEqual(len(self.profile["criteria"]), 39)
        self.assertIn({"profile_id": "software-quality", "version": "1.0.0"}, self.profile["lineage"])
        self.assertIn({"profile_id": "ux-engineering", "version": "1.0.0"}, self.profile["lineage"])
        self.assertEqual(validate_lifecycle_binding("ux-engineering", "ux-engineering"), [])

    def test_pos_and_saas_opt_into_ux_profile(self):
        for profile_id in ("point-of-sale", "saas"):
            profile = load_profile(profile_id)
            controls = {item["id"] for item in profile["controls"]}
            self.assertTrue({item["id"] for item in self.profile["criteria"]} <= controls)
            self.assertIn({"profile_id": "ux-engineering", "version": "1.0.0"}, profile["lineage"])

    def test_complete_ux_assessment_passes(self):
        result = self.result()
        self.assertTrue(result["valid"])
        self.assertEqual(result["intrinsic"], "conformant")
        self.assertIn("declared_users_journeys_contexts", result["relational"])

    def test_required_ux_scope_is_exact(self):
        value = copy.deepcopy(self.assessment)
        value["criterion_scopes"].pop()
        self.assertFalse(self.result(value)["checks"]["exact_applicable_ux_scope_set"])
        value = copy.deepcopy(self.assessment)
        value["criterion_scopes"].append(copy.deepcopy(value["criterion_scopes"][0]))
        self.assertFalse(self.result(value)["checks"]["unique_scope_bindings"])

    def test_scope_cannot_claim_undeclared_population_or_wrong_evidence(self):
        value = copy.deepcopy(self.assessment)
        value["criterion_scopes"][0]["population_ids"] = ["unresearched-customer"]
        self.assertFalse(self.result(value)["checks"]["evidence_scope_binding"])
        value = copy.deepcopy(self.assessment)
        value["criterion_scopes"][0]["evidence_digest"] = digest("other evidence")
        self.assertFalse(self.result(value)["checks"]["evidence_scope_binding"])

    def test_instrument_score_requires_declared_instrument(self):
        value = copy.deepcopy(self.assessment)
        scope = next(item for item in value["criterion_scopes"] if item["criterion_id"] == "ux-cognitive-load")
        scope["instrument_id"] = "undeclared-instrument"
        self.assertFalse(self.result(value)["checks"]["declared_instrument_binding"])

    def test_research_ethics_must_precede_assessment(self):
        value = copy.deepcopy(self.assessment)
        value["research_ethics"]["approved_at"] = self.now + 1
        self.assertFalse(self.result(value)["checks"]["research_ethics_authorized_before_assessment"])

    def test_nested_quality_failure_fails_closed(self):
        value = copy.deepcopy(self.assessment)
        value["quality_assessment"]["observations"][0]["expires_at"] = self.now - 1
        result = self.result(value)
        self.assertFalse(result["valid"])
        self.assertFalse(result["checks"]["quality_assessment"])

    def test_change_triggers_reassess_relevant_ux(self):
        from clses_mvas_v1.quality import affected_criteria
        affected = affected_criteria(self.profile, ["user_population"])
        self.assertIn("ux-user-research-coverage", affected)
        self.assertIn("ux-critical-journey-success", affected)
        self.assertIn("ux-localized-journey-success", affected)
        self.assertIn("ux-ai-decision-understanding", affected)


if __name__ == "__main__":
    unittest.main()
