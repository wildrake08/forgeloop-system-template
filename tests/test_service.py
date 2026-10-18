import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from service import calculate

class ServiceTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calculate(2, 3), 5)
