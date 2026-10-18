import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import kernel_tests.test_ux as ux_test_helpers


class UxCliTest(unittest.TestCase):
    def run_cli(self, *args, check=True):
        return subprocess.run([sys.executable, "-m", "clses_mvas_v1.ux", *args], capture_output=True, text=True, check=check)

    def test_help(self):
        self.assertIn("clses-ux", self.run_cli("--help").stdout)

    def test_applicable_and_affected(self):
        applicable = json.loads(self.run_cli("applicable", "--context-tag", "ai_mediated").stdout)
        self.assertIn("ux-ai-decision-understanding", applicable["criteria"])
        affected = json.loads(self.run_cli("affected", "--change-kind", "navigation").stdout)
        self.assertIn("ux-findability", affected["criteria"])

    def test_assess(self):
        fixture = ux_test_helpers.UxEngineeringProfileTest()
        fixture.setUp()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "ux-assessment.json"
                path.write_text(json.dumps(fixture.assessment))
                result = self.run_cli("assess", str(path))
                self.assertTrue(json.loads(result.stdout)["valid"])
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
