import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clses_mvas_v1.discovery import discover_environment


class DiscoveryTest(unittest.TestCase):
    def test_detects_files_without_reading_secret_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);(root / "pyproject.toml").write_text("[project]\nname='sample'\n");(root / "Dockerfile").write_text("FROM scratch\n")
            with patch.dict(os.environ, {"CI": "TOP-SECRET-VALUE"}, clear=False):
                result = discover_environment(root, now=100)
            self.assertEqual(result["status"], "proposed_not_authorized")
            self.assertIn("python", result["suggested_facts"]["operating_conditions"]["detected_capabilities"])
            self.assertIn("container", result["suggested_facts"]["operating_conditions"]["detected_capabilities"])
            self.assertNotIn("TOP-SECRET-VALUE", str(result))
            self.assertTrue(next(item for item in result["environment_key_presence"] if item["name"] == "CI")["present"])

    def test_missing_source_fails(self):
        with self.assertRaises(ValueError):
            discover_environment("/definitely/not/a/clses/source")


if __name__ == "__main__":
    unittest.main()
