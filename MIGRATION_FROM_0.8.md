# Migration from 0.8

Version 1.0 is a new state model; `.clses` state from 0.8 is not upgraded in place.

1. Retain the 0.8 project and evidence as an immutable historical release.
2. Translate the accepted 0.8 blueprint to `CLSES-system-spec/v1`.
3. Initialize an empty v1 repository with that specification.
4. Import source and tests only through individually traced, authorized v1 work requests.
5. Run an exact-change build, acceptance, deployment, observation, and closure cycle.
6. Compare the resulting A1–A8 manifest and behavioral tests against the 0.8 baseline.
7. Switch governance only after v1 verifies; do not copy local signing keys between trust roots.

Historical 0.8 record digests may be listed as external provenance, but they do not become v1 signed records merely by copying them.
