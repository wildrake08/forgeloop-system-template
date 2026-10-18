# Preconfigured Production Adapters

CLSES 4.5 packages six production evidence-adapter families: CI verification, supply-chain assurance, deployment state, operations telemetry, resilience exercises, and UX research.

They are preconfigured protocol implementations, not pre-trusted integrations. Each organization must instantiate a family with its own externally managed RSA public key:

```sh
clses-adapters catalog
clses-adapters instantiate \
  --template ci-verification \
  --public-key ./ci-evidence-public.pem \
  --output ./ci-adapter.json
```

An evidence producer emits `CLSES-production-observation/v1` JSON and signs the exact file bytes with the corresponding private key. The adapter request supplies only the observation and detached-signature paths. Execution verifies the public-key trust anchor, detached RSA-SHA256 signature, normative schema, exact system/environment/artifact/evidence-type binding, a positive current observation, request deadline, and non-empty measurements.

The validated result enters the existing strict adapter protocol as criterion-specific evidence. Signature failure, key substitution, request rebinding, stale evidence, a failing observation, malformed measurements, or undeclared capability fails closed.

The adapters never embed private keys, vendor credentials, or universal trust. Authentic producer configuration, protected keys, target-environment access, and evidence-method validity remain organizational responsibilities.
