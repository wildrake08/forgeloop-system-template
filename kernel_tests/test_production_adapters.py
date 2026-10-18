import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from clses_mvas_v1.adapters import run_adapter
from clses_mvas_v1.production_adapters import instantiate_adapter, load_catalog


class ProductionAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.root = Path(self.temp.name);self.now = int(time.time())
        self.private = self.root / "private.pem";self.public = self.root / "public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(self.private)], check=True, capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)], check=True, capture_output=True)
        self.manifest = instantiate_adapter("ci-verification", self.public)
        self.evidence = self.root / "evidence.json";self.signature = self.root / "evidence.sig"
        self.observation = {"format": "CLSES-production-observation/v1", "producer_id": "trusted-ci", "system_id": "coffee-pos", "environment_id": "production", "artifact_id": "artifact-1", "evidence_type": "test_result", "passed": True, "measurements": {"tests": 212}, "observed_at": self.now - 1, "expires_at": self.now + 120}
        self.evidence.write_text(json.dumps(self.observation))
        subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(self.private), "-out", str(self.signature), str(self.evidence)], check=True, capture_output=True)
        self.request = {"format": "CLSES-adapter-request/v1", "request_id": "production-1", "system_id": "coffee-pos", "environment_id": "production", "control_id": "verification-effective", "artifact_id": "artifact-1", "evidence_type": "test_result", "inputs": {"evidence_file": str(self.evidence), "signature_file": str(self.signature)}, "deadline": self.now + 180}

    def tearDown(self):self.temp.cleanup()

    def test_six_preconfigured_adapter_families(self):
        self.assertEqual(len(load_catalog()), 6)

    def test_signed_observation_round_trip(self):
        result = run_adapter(self.manifest, self.request, self.now)
        self.assertTrue(result["passed"]);self.assertEqual(result["measurements"]["tests"], 212)

    def test_signature_tampering_fails(self):
        self.observation["measurements"]["tests"] = 0;self.evidence.write_text(json.dumps(self.observation))
        with self.assertRaises(RuntimeError):run_adapter(self.manifest, self.request, self.now)

    def test_request_binding_fails(self):
        value = dict(self.request);value["artifact_id"] = "other-artifact"
        with self.assertRaises(RuntimeError):run_adapter(self.manifest, value, self.now)

    def test_public_key_is_external_trust_anchor(self):
        other_private = self.root / "other-private.pem";other_public = self.root / "other-public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(other_private)], check=True, capture_output=True)
        subprocess.run(["openssl", "pkey", "-in", str(other_private), "-pubout", "-out", str(other_public)], check=True, capture_output=True)
        manifest = instantiate_adapter("ci-verification", other_public)
        with self.assertRaises(RuntimeError):run_adapter(manifest, self.request, self.now)


if __name__ == "__main__":unittest.main()
