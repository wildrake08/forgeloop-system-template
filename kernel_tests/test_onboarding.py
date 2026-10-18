import copy
import tempfile
import unittest
from pathlib import Path

from clses_mvas_v1.discovery import discover_environment
from clses_mvas_v1.intake import AUTHORITY_ROLES
from clses_mvas_v1.onboarding import apply_onboarding, list_templates, plan_onboarding


def complete_answers():
    return {
        "system_name": "Coffee Cart POS", "problem": "Checkout is slow", "beneficiaries": ["barista", "customer"],
        "outcome_statement": "Reduce checkout time", "outcome_metric": "checkout_seconds", "outcome_unit": "seconds",
        "outcome_operator": "<=", "outcome_target": 45, "outcome_baseline": 80,
        "data_classes": ["payment token", "transaction"], "compliance_obligations": ["payment-provider contract"],
        "operating_conditions": {"location": "mobile cart", "connectivity": "intermittent"},
        "authorities": {role: "person-" + role for role in AUTHORITY_ROLES},
    }


class OnboardingTest(unittest.TestCase):
    def test_three_packaged_templates_are_valid(self):
        templates = list_templates()
        self.assertEqual({item["id"] for item in templates}, {"coffee-cart-pos", "saas-web", "general-interactive"})

    def test_incomplete_plan_lists_only_missing_human_inputs(self):
        plan = plan_onboarding("coffee-cart-pos", {"system_name": "Coffee Cart"})
        self.assertEqual(plan["status"], "needs_human_input")
        self.assertNotIn("system_name", {item["fact_id"] for item in plan["missing_inputs"]})
        self.assertEqual(plan["authority_effect"].split(";")[0], "none")

    def test_complete_plan_derives_safe_identifiers(self):
        plan = plan_onboarding("coffee-cart-pos", complete_answers())
        self.assertEqual(plan["status"], "ready_to_begin")
        self.assertEqual(plan["facts"]["system_id"], "coffee-cart-pos")
        self.assertEqual(plan["facts"]["purpose"], "Address: Checkout is slow")

    def test_apply_starts_ready_guided_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            result = apply_onboarding(folder, "coffee-cart-pos", complete_answers())
            self.assertEqual(result["view"]["intake"]["question_count"], 0)
            self.assertEqual(result["view"]["current_step"], "authorize_product_baseline")
            self.assertEqual(result["view"]["intake"]["baseline"]["decision"], "proposed_not_authorized")

    def test_discovery_requires_explicit_acceptance_and_digest_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);(root / "package.json").write_text("{}")
            report = discover_environment(root, now=100)
            ignored = plan_onboarding("saas-web", {}, report, accept_discovery=False)
            self.assertNotIn("operating_conditions", ignored["facts"])
            accepted = plan_onboarding("saas-web", {}, report, accept_discovery=True)
            self.assertEqual(accepted["accepted_discovery_digest"], report["report_digest"])
            self.assertIn("operating_conditions", accepted["facts"])
            tampered = copy.deepcopy(report);tampered["suggested_facts"]["system_class"] = "unsafe-rewrite"
            with self.assertRaises(ValueError):plan_onboarding("saas-web", {}, tampered, accept_discovery=True)


if __name__ == "__main__":
    unittest.main()
