import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import kernel_tests.test_quality as quality_test_helpers


class QualityCliTest(unittest.TestCase):
    def run_cli(self, *args, check=True):
        return subprocess.run([sys.executable, "-m", "clses_mvas_v1.quality", *args], capture_output=True, text=True, check=check)

    def test_help(self):
        self.assertIn("clses-quality", self.run_cli("--help").stdout)

    def test_applicable_and_affected(self):
        applicable = json.loads(self.run_cli("applicable", "--context-tag", "safety_relevant").stdout)
        self.assertIn("quality-fail-safe", applicable["criteria"])
        affected = json.loads(self.run_cli("affected", "--change-kind", "dependency").stdout)
        self.assertIn("quality-replaceability", affected["criteria"])

    def test_assess(self):
        fixture = quality_test_helpers.SoftwareQualityProfileTest()
        fixture.setUp()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "assessment.json"
                path.write_text(json.dumps(fixture.assessment))
                result = self.run_cli("assess", str(path))
                self.assertTrue(json.loads(result.stdout)["valid"])
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
