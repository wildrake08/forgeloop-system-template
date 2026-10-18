# CLSES Guided Operator

Version 4.5 adds the same journey as a loopback visual interface plus onboarding-template and environment-discovery commands. See `ONBOARDING_AND_VISUAL_OPERATOR.md`. The command and visual surfaces delegate to this operator; neither has independent authority.

`clses-operator` is the thin human-facing layer over intake, the lifecycle copilot, autonomous execution, and the authoritative control plane. It presents one journey and one status view while leaving the underlying controls intact.

## The seven-step journey

1. Understand the need.
2. Authorize the exact product baseline.
3. Authorize bounded engineering.
4. Engineer and verify.
5. Authorize the exact build.
6. Accept the artifact and authorize deployment.
7. Operate, measure outcomes, and reassess changes.

At every point `status` returns a headline, current step, progress, one recommended next action, open intake questions, actionable authority requests, a plain evidence summary, and the authority notice. Technical digests remain available in the same result for traceability.

## Begin in an empty repository

```sh
clses-operator --root ./coffee-pos setup \
  --system-id coffee-pos \
  --purpose "Operate a coffee cart point of sale" \
  --beneficiary "coffee-cart operator"

clses-operator --root ./coffee-pos begin --profile point-of-sale
clses-operator --root ./coffee-pos status
```

`begin` applies the minimum-question intake policy. For an empty point-of-sale context, the result contains five consolidated question groups. Supply answers as one JSON object:

```sh
clses-operator --root ./coffee-pos answer --file intake-answers.json
```

The resulting minimum viable baseline remains `proposed_not_authorized`. An authenticated `owner` must use `authorizations` and the exact decision challenge to authorize that digest-bound product baseline. Mandate preparation fails closed until this product decision exists. Product-baseline authorization does not authorize engineering, release, or deployment.

## Authenticate and prepare work

```sh
clses-operator --root ./coffee-pos session-open \
  --principal engineering-reviewer \
  --credential-file ./coffee-pos/.clses-v1/keys/engineering-reviewer.key

clses-operator --root ./coffee-pos mandate \
  --session SESSION --token TOKEN --file mandate.json
```

The mandate response contains an exact approval and rejection challenge. The reviewer uses `decide`; ordinary conversation has no effect:

```sh
clses-operator --root ./coffee-pos decide \
  --session SESSION --token TOKEN \
  --decision-id DECISION \
  --outcome approve \
  --confirmation 'APPROVE DECISION PROPOSAL_DIGEST'

clses-operator --root ./coffee-pos continue \
  --session SESSION --token TOKEN --run-id RUN
```

An owner registers the chosen execution agent once through the same surface with `driver-register`. `--kind codex` uses the built-in adapter; `--kind generic` accepts a JSON argument array containing `{prompt}`.

## Consolidated authorization review

When the run reaches an authority boundary:

```sh
clses-operator --root ./coffee-pos authorizations \
  --session SESSION --token TOKEN
```

The command creates one review packet for the authenticated principal. The owner receives the baseline decision; the engineering reviewer receives the build decision with the complete bounded trial transcript and digests; at release, one packet contains both artifact acceptance and deployment authorization together with the bound artifact and build-test transcript. Consolidation reduces navigation; it does not merge authority. Each item retains its own scope, decision ID, evidence, approve challenge, reject challenge, role check, and replay protection.

When execution establishes an architecture and implementation language, the operator marks the corresponding safe defaults as replaced by execution evidence and removes them from the deferred list. The authorized product-intent fields remain immutable. After closure, progress is seven of seven and the status reads “Cycle closed; continuous monitoring and change-triggered reassessment are active.” Monitoring is ongoing, not an unfinished authorization step.

Preparing or reading a packet grants nothing. Every item must be explicitly decided. A packet cannot include a decision assigned to another principal, and repeated preparation reuses an existing unresolved proposal instead of creating duplicate requests.

## Conversational turns

The deterministic `turn` operation supports `status`, `begin intake`, `answer intake`, `reassess intake`, and `prepare authorizations`. Structured data is supplied through `--data-file`. The `reassess` command provides the same change-triggered reopening without a conversation. Ambiguous language is read-only. Statements such as “I approve” are explicitly rejected as authority and direct the person to the exact decision challenge.

```sh
clses-operator --root ./coffee-pos turn \
  --session SESSION --token TOKEN --message "status"
```

An optional external LLM facilitator may still be connected through `clses-copilot`. It can explain the guided view, but it cannot change routing, create arbitrary scopes, authenticate a human, or approve a decision.

## Production boundary

The reference operator uses local credential possession, bearer session tokens, a command-line JSON view, a local simulated deployment, and deterministic phrase routing. A production user interface should render the same operator contract, connect decisions to organizational identity and MFA, protect tokens and signing keys, and supply authentic target-environment evidence adapters. The thin layer does not convert the reference demonstration into universal production certification.
