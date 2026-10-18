# Minimal-Viability Intake

CLSES 4.1 asks only for missing information that is required by the composed lifecycle profile, material to the system, not reliably derivable, and unsafe to defer.

For the base production and point-of-sale profiles, an empty context produces five consolidated question groups: need and beneficiaries; measurable outcome; data and compliance exposure; operating conditions; and consequential authorities. Already-known facts suppress their questions. Partial answers retain the same stable question identifier rather than producing duplicates.

The intake engine derives system class from the selected profile, derives a stable system identifier and draft purpose, and applies only policy-declared safe reversible defaults. Every default is recorded as an owned, confidence-scored, expiring assumption. Expired defaults are explicitly reevaluated against their unchanged policy basis. Technical choices that are not needed for viability are deferred.

Purpose, beneficiaries, outcome targets, data exposure, operating conditions, and authority identities have no silent defaults. Conflicting values produce a resolution question. Answers that were not requested are rejected, preventing the intake interaction from becoming an ungoverned configuration channel.

Once the minimum facts are complete, the engine emits one consolidated `CLSES-minimum-viable-baseline/v1` proposal. Its decision begins as `proposed_not_authorized`; conversation and silence never approve it. The owner must explicitly approve its stable product-intent digest through the authority plane. The engine blocks every guided mandate, including a direct-engine bypass attempt, until that exact authorization exists. Execution-derived architecture and language facts may resolve reversible assumptions without changing the authorized product intent; their evidence source and resolution time remain visible.

Material changes name affected facts. Only those facts and dependent conclusions are reopened. The engine preserves its question history, invalidates affected assumptions, and prepares a new proposal after resolution.

Example:

```sh
clses-intake start --profile point-of-sale --output intake.json
clses-intake answer intake.json answers.json
clses-intake status intake.json
clses-intake reassess intake.json change.json
```
