"""Preconfigured adapters for externally signed production observations."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from jsonschema import Draft202012Validator

from .adapters import run_adapter
from .store import canonical, digest, write


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "adapter_templates" / "catalog.json"
OBSERVATION_SCHEMA = ROOT / "schemas" / "production-observation.schema.json"


def load_catalog():
    value = json.loads(CATALOG.read_text())
    ids = [item["id"] for item in value]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate production adapter template")
    return value


def instantiate_adapter(template_id, public_key_file):
    template = next((item for item in load_catalog() if item["id"] == template_id), None)
    if template is None:
        raise ValueError("unknown production adapter template")
    public_key = Path(public_key_file).resolve()
    if not public_key.is_file():
        raise ValueError("production adapter requires an existing public key file")
    core = {
        "format": "CLSES-adapter-manifest/v1",
        "id": "production-" + template_id,
        "version": template["version"],
        "capabilities": template["capabilities"],
        "trust_anchor": digest(public_key.read_bytes()),
        "execution_boundary": "read_only",
        "command": [
            sys.executable, "-m", "clses_mvas_v1.production_adapters", "run",
            "--request", "{request}", "--output", "{output}",
            "--adapter-id", "{adapter_id}", "--adapter-digest", "{adapter_digest}",
            "--trust-anchor", "{trust_anchor}", "--public-key", str(public_key),
        ],
        "timeout_seconds": 60,
    }
    return {**core, "digest": digest(core)}


def _verify_observation(request, adapter_id, adapter_digest, trust_anchor, public_key_file, now=None):
    now = int(time.time()) if now is None else int(now)
    inputs = request.get("inputs", {})
    if set(inputs) != {"evidence_file", "signature_file"}:
        raise ValueError("signed production adapter requires evidence_file and signature_file only")
    evidence_path = Path(inputs["evidence_file"]).resolve()
    signature_path = Path(inputs["signature_file"]).resolve()
    public_key = Path(public_key_file).resolve()
    if not evidence_path.is_file() or not signature_path.is_file() or not public_key.is_file():
        raise ValueError("production evidence, signature, and public key files must exist")
    if digest(public_key.read_bytes()) != trust_anchor:
        raise ValueError("production public key does not match adapter trust anchor")
    verification = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", str(public_key), "-signature", str(signature_path), str(evidence_path)],
        capture_output=True,
    )
    if verification.returncode != 0:
        raise ValueError("production evidence signature is invalid")
    observation = json.loads(evidence_path.read_text())
    errors = sorted(Draft202012Validator(json.loads(OBSERVATION_SCHEMA.read_text())).iter_errors(observation), key=lambda error: list(error.path))
    if errors:
        raise ValueError("normative production-observation.schema.json failure: " + errors[0].message)
    matches = (
        observation["evidence_type"] == request["evidence_type"]
        and observation["system_id"] == request["system_id"]
        and observation["environment_id"] == request["environment_id"]
        and observation["artifact_id"] == request["artifact_id"]
        and observation["observed_at"] <= now <= observation["expires_at"] <= request["deadline"]
        and observation["passed"] is True
    )
    if not matches:
        raise ValueError("signed production observation is failing, stale, or not bound to the request")
    return {
        "format": "CLSES-adapter-result/v1", "request_id": request["request_id"],
        "adapter_id": adapter_id, "adapter_digest": adapter_digest, "evidence_type": observation["evidence_type"],
        "passed": True, "measurements": observation["measurements"],
        "raw_evidence_sha256": digest(evidence_path.read_bytes()), "observed_at": observation["observed_at"],
        "expires_at": observation["expires_at"],
    }


def main():
    parser = argparse.ArgumentParser(prog="clses-adapters", description="Preconfigured signed production evidence adapters")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    item = sub.add_parser("instantiate")
    item.add_argument("--template", required=True);item.add_argument("--public-key", required=True);item.add_argument("--output", required=True)
    item = sub.add_parser("execute")
    item.add_argument("--manifest", required=True);item.add_argument("--request", required=True)
    item = sub.add_parser("run", help=argparse.SUPPRESS)
    item.add_argument("--request", required=True);item.add_argument("--output", required=True);item.add_argument("--adapter-id", required=True)
    item.add_argument("--adapter-digest", required=True);item.add_argument("--trust-anchor", required=True);item.add_argument("--public-key", required=True)
    args = parser.parse_args()
    if args.command == "catalog":
        result = load_catalog()
    elif args.command == "instantiate":
        result = instantiate_adapter(args.template, args.public_key);write(args.output, result)
    elif args.command == "execute":
        result = run_adapter(json.loads(Path(args.manifest).read_text()), json.loads(Path(args.request).read_text()))
    else:
        request = json.loads(Path(args.request).read_text())
        result = _verify_observation(request, args.adapter_id, args.adapter_digest, args.trust_anchor, args.public_key)
        write(args.output, result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
