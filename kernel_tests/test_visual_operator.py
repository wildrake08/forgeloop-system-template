import tempfile
import unittest

from clses_mvas_v1.visual_operator import VisualOperatorService
from kernel_tests.test_onboarding import complete_answers


class VisualOperatorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.service = VisualOperatorService(self.temp.name, csrf_token="test-csrf")

    def tearDown(self):
        self.temp.cleanup()

    def test_uninitialized_view_and_catalogs(self):
        status = self.service.dispatch("GET", "/api/status")
        self.assertFalse(status["initialized"])
        self.assertEqual(len(self.service.dispatch("GET", "/api/templates")), 3)
        self.assertEqual(len(self.service.dispatch("GET", "/api/adapters")), 6)

    def test_mutation_requires_csrf(self):
        with self.assertRaises(PermissionError):
            self.service.dispatch("POST", "/api/discover", {})
        result = self.service.dispatch("POST", "/api/discover", {}, csrf="test-csrf")
        self.assertEqual(result["status"], "proposed_not_authorized")

    def test_index_embeds_token_and_security_notice(self):
        page = self.service.index()
        self.assertIn('data-csrf="test-csrf"', page)
        self.assertIn("never authorize", page)

    def test_unknown_endpoint_fails(self):
        with self.assertRaises(ValueError):self.service.dispatch("GET", "/api/missing")

    def test_visual_onboarding_reaches_authority_step(self):
        result = self.service.dispatch("POST", "/api/onboarding/apply", {"template_id": "coffee-cart-pos", "answers": complete_answers()}, csrf="test-csrf")
        self.assertEqual(result["view"]["current_step"], "authorize_engineering")
        status = self.service.dispatch("GET", "/api/status")
        self.assertTrue(status["initialized"])
        self.assertEqual(status["current_step"], "authorize_engineering")


if __name__ == "__main__":
    unittest.main()
