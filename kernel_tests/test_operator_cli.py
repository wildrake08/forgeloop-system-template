import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel_tests.test_onboarding import complete_answers


class OperatorCliTest(unittest.TestCase):
    def run_cli(self, *args, check=True):
        return subprocess.run([sys.executable, "-m", "clses_mvas_v1.operator_cli", *args], capture_output=True, text=True, check=check)

    def test_help_describes_guided_operator(self):
        result = self.run_cli("--help")
        self.assertIn("clses-operator", result.stdout)
        self.assertIn("Guided CLSES lifecycle", result.stdout)

    def test_setup_and_status_use_one_command_surface(self):
        with tempfile.TemporaryDirectory() as folder:
            setup = json.loads(self.run_cli("--root", folder, "setup", "--system-id", "coffee-pos").stdout)
            self.assertEqual(setup["next"]["action"], "begin")
            status = json.loads(self.run_cli("--root", folder, "status").stdout)
            self.assertEqual(status["current_step"], "understand_the_need")

    def test_begin_returns_plain_intake_status(self):
        with tempfile.TemporaryDirectory() as folder:
            self.run_cli("--root", folder, "setup")
            view = json.loads(self.run_cli("--root", folder, "begin", "--profile", "point-of-sale").stdout)
            self.assertEqual(view["intake"]["question_count"], 5)
            self.assertEqual(view["next"]["action"], "answer")

    def test_uninitialized_workspace_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_cli("--root", folder, "status", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error", json.loads(result.stderr))

    def test_templates_discovery_and_onboarding_use_same_surface(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as inputs:
            templates = json.loads(self.run_cli("--root", folder, "templates").stdout)
            self.assertEqual(len(templates), 3)
            discovery = json.loads(self.run_cli("--root", folder, "discover").stdout)
            self.assertEqual(discovery["status"], "proposed_not_authorized")
            answers = Path(inputs) / "answers.json";answers.write_text(json.dumps(complete_answers()))
            result = json.loads(self.run_cli("--root", folder, "onboard", "--template", "coffee-cart-pos", "--answers", str(answers)).stdout)
            self.assertEqual(result["view"]["current_step"], "authorize_engineering")


if __name__ == "__main__":
    unittest.main()
