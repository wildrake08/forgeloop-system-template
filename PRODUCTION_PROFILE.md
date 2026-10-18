# CLSES Production Evidence Profile 2.0

The production verifier is deliberately fail-closed. It never converts a generic test exit code or health check into arbitrary criterion evidence. Every declared criterion requires one fresh, criterion-specific observation naming its method, adapter digest, environment, raw-evidence digest, measurement, unit, coverage, source, and expiry.

A positive production verdict additionally requires exact equality among declared components, artifact entries, and the current deployment; externally anchored evidence signature; artifact acceptance evidence; deployment authorization; active change monitors for source, dependencies, infrastructure, runtime, security, and regulation; SBOM and supply-chain evidence; rollback and restore tests; active operations monitoring; no open critical incidents; and an exact closure decision.

The trusted public key is supplied separately from the evidence bundle. This prevents a bundle from declaring its own trust anchor. When any observation or monitor expires, or when deployed bytes change, verification returns `not_adequate`.

This profile makes CLSES applicable across software-system types through adapters. It does not claim that an unevaluated system is adequate. Each organization must supply authentic adapters and evidence from the declared production environment.
