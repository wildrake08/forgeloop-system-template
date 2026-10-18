"""Loopback-only visual operator over the same guided lifecycle services."""
from __future__ import annotations

import argparse
import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .discovery import discover_environment
from .guided_operator import GuidedOperator
from .onboarding import apply_onboarding, list_templates, plan_onboarding
from .production_adapters import load_catalog


ASSET_DIR = Path(__file__).resolve().parent / "operator_ui"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class VisualOperatorService:
    def __init__(self, root, csrf_token=None):
        self.root = Path(root).resolve()
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)

    def _operator(self):
        return GuidedOperator(self.root)

    def dispatch(self, method, path, payload=None, csrf=None):
        payload = payload or {}
        if method != "GET" and csrf != self.csrf_token:
            raise PermissionError("valid visual-operator CSRF token required")
        if method == "GET" and path == "/api/status":
            if not (self.root / ".clses-v1").exists():
                return {"initialized": False, "headline": "Choose an onboarding template to begin.", "current_step": "onboarding", "authority_notice": "Templates and discovery prepare proposals only; they never authorize."}
            return {"initialized": True, **self._operator().status()}
        if method == "GET" and path == "/api/templates":
            return list_templates()
        if method == "GET" and path == "/api/adapters":
            return load_catalog()
        if method == "POST" and path == "/api/discover":
            return discover_environment(payload.get("source_root", str(self.root)))
        if method == "POST" and path == "/api/onboarding/plan":
            return plan_onboarding(payload["template_id"], payload.get("answers"), payload.get("discovery"), payload.get("accept_discovery", False))
        if method == "POST" and path == "/api/onboarding/apply":
            return apply_onboarding(self.root, payload["template_id"], payload.get("answers", {}), payload.get("discovery"), payload.get("accept_discovery", False))
        if method == "POST" and path == "/api/intake/answer":
            return self._operator().answer(payload["answers"])
        if method == "POST" and path == "/api/session":
            return self._operator().open_session(payload["principal"], payload["credential"], payload.get("ttl", 3600))
        if method == "POST" and path == "/api/driver":
            return self._operator().register_driver(payload["session_id"], payload["token"], payload["name"], payload.get("kind", "codex"), payload.get("argv"))
        if method == "POST" and path == "/api/mandate":
            return self._operator().propose_mandate(payload["session_id"], payload["token"], payload["mandate"])
        if method == "POST" and path == "/api/authorizations":
            return self._operator().prepare_authorizations(payload["session_id"], payload["token"], payload.get("evidence"))
        if method == "POST" and path == "/api/decide":
            return self._operator().decide(payload["session_id"], payload["token"], payload["decision_id"], payload["outcome"], payload["confirmation"])
        if method == "POST" and path == "/api/continue":
            return self._operator().continue_run(payload["session_id"], payload["token"], payload["run_id"])
        raise ValueError("unknown visual operator endpoint")

    def index(self):
        return (ASSET_DIR / "index.html").read_text().replace("@@CSRF@@", self.csrf_token)


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        def _headers(self, status, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path == "/":
                    body = service.index().encode();content_type = "text/html; charset=utf-8"
                elif path == "/app.css":
                    body = (ASSET_DIR / "app.css").read_bytes();content_type = "text/css; charset=utf-8"
                elif path == "/app.js":
                    body = (ASSET_DIR / "app.js").read_bytes();content_type = "text/javascript; charset=utf-8"
                else:
                    body = json.dumps(service.dispatch("GET", path)).encode();content_type = "application/json"
                self._headers(200, content_type);self.wfile.write(body)
            except Exception as exc:
                body = json.dumps({"error": str(exc)}).encode();self._headers(400, "application/json");self.wfile.write(body)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1_000_000:
                    raise ValueError("request is too large")
                payload = json.loads(self.rfile.read(length) or b"{}")
                result = service.dispatch("POST", urlparse(self.path).path, payload, self.headers.get("X-CLSES-CSRF"))
                body = json.dumps(result).encode();self._headers(200, "application/json");self.wfile.write(body)
            except Exception as exc:
                body = json.dumps({"error": str(exc)}).encode();self._headers(400, "application/json");self.wfile.write(body)

        def log_message(self, format, *args):
            return
    return Handler


def serve(root, host="127.0.0.1", port=8765):
    if host not in LOOPBACK:
        raise ValueError("visual operator may bind only to a loopback address")
    service = VisualOperatorService(root)
    server = ThreadingHTTPServer((host, port), handler_for(service))
    print(json.dumps({"url": f"http://{host}:{server.server_port}/", "root": str(service.root), "authority_notice": "The UI cannot infer or merge authority decisions."}), flush=True)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(prog="clses-operator-ui", description="Local visual interface for the guided CLSES lifecycle")
    parser.add_argument("--root", default=".");parser.add_argument("--host", default="127.0.0.1");parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args();serve(args.root, args.host, args.port);return 0


if __name__ == "__main__":
    raise SystemExit(main())
