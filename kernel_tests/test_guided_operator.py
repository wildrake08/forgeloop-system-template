import sys
import tempfile
import time
import unittest
from pathlib import Path

from clses_mvas_v1.engine import Engine
from clses_mvas_v1.guided_operator import GuidedOperator
from clses_mvas_v1.intake import AUTHORITY_ROLES


def complete_facts():
    return {
        "system_name": "Coffee Cart POS",
        "problem": "Manual checkout is slow and error prone",
        "beneficiaries": ["operator", "customer"],
        "outcome_statement": "Reduce representative checkout time",
        "outcome_metric": "checkout_time_seconds",
        "outcome_unit": "seconds",
        "outcome_operator": "<=",
        "outcome_target": 45,
        "outcome_baseline": 80,
        "data_classes": ["payment token", "transaction record"],
        "compliance_obligations": ["payment-provider contract"],
        "operating_conditions": {"location": "mobile cart", "connectivity": "intermittent"},
        "authorities": {role: "person-" + role for role in AUTHORITY_ROLES},
    }


class GuidedOperatorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        Engine(self.root).init(system_id="guided-test")
        self.operator = GuidedOperator(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def session(self, principal):
        credential = (self.root / ".clses-v1" / "keys" / (principal + ".key")).read_text()
        opened = self.operator.open_session(principal, credential)
        return opened["session_id"], opened["token"]

    def ready_intake(self):
        return self.operator.begin("point-of-sale", {"facts": complete_facts()}, now=100)

    def mandate(self):
        return {
            "run_id": "guided-run",
            "objective": "Verify the guided controlled lifecycle",
            "driver": "guided-driver",
            "allowed_paths": ["tests/*"],
            "requirements": ["test_pass_rate"],
            "max_iterations": 2,
            "max_changes": 2,
            "max_bytes": 2000,
            "expires_at": int(time.time()) + 3600,
        }

    def test_initial_status_is_plain_and_actionable(self):
        view = self.operator.status()
        self.assertEqual(view["current_step"], "understand_the_need")
        self.assertEqual(view["next"]["action"], "begin")
        self.assertIn("never authorize", view["authority_notice"])

    def test_empty_intake_is_presented_as_five_consolidated_groups(self):
        view = self.operator.begin("point-of-sale", now=100)
        self.assertEqual(view["intake"]["question_count"], 5)
        self.assertEqual(view["next"]["action"], "answer")

    def test_complete_intake_moves_to_one_mandate_step(self):
        view = self.ready_intake()
        self.assertEqual(view["intake"]["question_count"], 0)
        self.assertEqual(view["current_step"], "authorize_engineering")
        self.assertEqual(view["intake"]["baseline"]["decision"], "proposed_not_authorized")

    def test_mandate_is_blocked_until_intake_is_complete(self):
        self.operator.begin("point-of-sale", now=100)
        session, token = self.session("engineering-reviewer")
        with self.assertRaises(PermissionError):
            self.operator.propose_mandate(session, token, self.mandate())

    def test_material_change_reopens_only_affected_intake(self):
        self.ready_intake()
        view = self.operator.reassess({"change_id": "conditions-2", "kind": "operating_change", "affected_facts": ["operating_conditions"], "reason": "cart now operates outdoors"}, now=200)
        self.assertEqual([question["id"] for question in view["intake"]["questions"]], ["resolve-conditions"])
        self.assertEqual(view["current_step"], "understand_the_need")

    def test_ambiguous_conversation_does_not_mutate_authority(self):
        session, token = self.session("engineering-reviewer")
        result = self.operator.turn(session, token, "I approve")
        self.assertFalse(result["authoritative"])
        self.assertIn("cannot treat conversation", result["response"])
        self.assertFalse((self.root / ".clses-v1" / "authorizations").exists())

    def test_turn_routes_status_without_state_change(self):
        session, token = self.session("operator")
        before = self.operator.store.verify_ledger()[1]
        result = self.operator.turn(session, token, "status")
        after = self.operator.store.verify_ledger()[1]
        self.assertFalse(result["authoritative"])
        self.assertEqual(before, after)

    def test_release_requests_are_consolidated_but_decided_separately(self):
        self.ready_intake()
        script = "import json;print(json.dumps({'status':'done','summary':'tests pass','changes':[]}))"
        owner, owner_token = self.session("owner")
        self.operator.register_driver(owner, owner_token, "guided-driver", "generic", [sys.executable, "-c", script, "{prompt}"])
        eng, eng_token = self.session("engineering-reviewer")
        release, release_token = self.session("release-owner")

        mandate = self.operator.propose_mandate(eng, eng_token, self.mandate())
        self.operator.decide(eng, eng_token, mandate["decision_id"], "approve", mandate["challenge"])
        first = self.operator.continue_run(eng, eng_token, "guided-run")["result"]
        self.assertEqual(first["phase"], "build")

        build_packet = self.operator.prepare_authorizations(eng, eng_token)
        self.assertEqual(len(build_packet["items"]), 1)
        self.assertFalse((self.root / ".clses-v1" / "authorizations").exists())
        build_item = build_packet["items"][0]
        self.operator.decide(eng, eng_token, build_item["decision_id"], "approve", build_item["approve_exactly"])

        second = self.operator.continue_run(eng, eng_token, "guided-run")["result"]
        self.assertEqual(second["phase"], "acceptance_and_release")
        release_packet = self.operator.prepare_authorizations(release, release_token)
        self.assertEqual(len(release_packet["items"]), 2)
        self.assertEqual({item["scope"].split(":", 1)[0] for item in release_packet["items"]}, {"accept", "deploy"})
        repeated = self.operator.prepare_authorizations(release, release_token)
        self.assertEqual(
            {item["decision_id"] for item in repeated["items"]},
            {item["decision_id"] for item in release_packet["items"]},
        )
        for item in release_packet["items"]:
            self.operator.decide(release, release_token, item["decision_id"], "approve", item["approve_exactly"])
        self.assertEqual(self.operator.status()["next"]["action"], "continue")
        final = self.operator.continue_run(release, release_token, "guided-run")["result"]
        self.assertTrue(final["valid"])
        self.assertEqual(self.operator.status()["current_step"], "operate_and_reassess")
        self.assertIn("closed", self.operator.status()["evidence"]["summary"])

    def test_wrong_principal_cannot_prepare_anothers_packet(self):
        self.ready_intake()
        release, token = self.session("release-owner")
        with self.assertRaises(ValueError):
            self.operator.prepare_authorizations(release, token)

    def test_duplicate_workflow_is_rejected(self):
        self.operator.begin("point-of-sale", now=100)
        with self.assertRaises(ValueError):
            self.operator.begin("point-of-sale", now=101)


if __name__ == "__main__":
    unittest.main()
