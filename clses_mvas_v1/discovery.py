"""Read-only, secret-safe local environment discovery."""
from __future__ import annotations

import json
import os
import platform
import shutil
import time
from pathlib import Path

from jsonschema import Draft202012Validator

from .store import digest


SCHEMA = Path(__file__).resolve().parent / "schemas" / "environment-discovery.schema.json"
INDICATORS = {
    "pyproject.toml": "python",
    "requirements.txt": "python",
    "package.json": "node",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "Dockerfile": "container",
    "compose.yaml": "compose",
    "docker-compose.yml": "compose",
    "terraform": "infrastructure_as_code",
    "k8s": "kubernetes",
    ".github/workflows": "github_actions",
}
RUNTIMES = ("python3", "node", "npm", "git", "docker", "kubectl", "terraform")
SAFE_ENV_KEYS = ("CI", "GITHUB_ACTIONS", "KUBERNETES_SERVICE_HOST", "CONTAINER", "TERM_PROGRAM")


def _validate(value):
    errors = sorted(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ValueError("normative environment-discovery.schema.json failure: " + errors[0].message)


def discover_environment(source_root, now=None):
    root = Path(source_root).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError("discovery source must be an existing directory")
    detected = []
    evidence = []
    for relative, capability in INDICATORS.items():
        path = root / relative
        if path.exists():
            detected.append(capability)
            if path.is_file():
                evidence.append({"path": relative, "kind": "file", "sha256": digest(path.read_bytes())})
            else:
                evidence.append({"path": relative, "kind": "directory", "sha256": digest(sorted(str(item.relative_to(root)) for item in path.rglob("*") if item.is_file()))})
    runtimes = [{"name": name, "available": shutil.which(name) is not None} for name in RUNTIMES]
    env_presence = [{"name": name, "present": name in os.environ} for name in SAFE_ENV_KEYS]
    operating = {
        "platform": platform.system().lower(),
        "architecture": platform.machine().lower(),
        "detected_capabilities": sorted(set(detected)),
        "available_runtimes": [item["name"] for item in runtimes if item["available"]],
    }
    suggested = {
        "system_name": root.name.replace("-", " ").replace("_", " ").title() or "New System",
        "system_class": "saas" if {"node", "github_actions"} <= set(detected) else "interactive-software",
        "operating_conditions": operating,
    }
    core = {
        "format": "CLSES-environment-discovery/v1",
        "source_root": str(root),
        "observed_at": int(time.time()) if now is None else int(now),
        "evidence": evidence,
        "runtimes": runtimes,
        "environment_key_presence": env_presence,
        "suggested_facts": suggested,
        "warnings": [
            "Discovery is local and read-only; it does not inspect environment-variable values or contact external services.",
            "Every suggested fact is proposed, not authoritative, and requires explicit human acceptance before intake use.",
        ],
        "status": "proposed_not_authorized",
    }
    result = {**core, "report_digest": digest(core)}
    _validate(result)
    return result
