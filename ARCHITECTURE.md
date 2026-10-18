# CLSES General Assurance Kernel Architecture

The v4.5 system adds a usability shell—onboarding templates, environment discovery, a visual operator, and preconfigured production adapters—over the v4.4 UX Engineering Profile, v4.3 software-quality profile, guided operator, minimal-viability engagement layer, and three stable layers: a small invariant assurance kernel, composable lifecycle profiles, and replaceable execution/evidence adapters. The usability shell prepares and presents; it does not replace the authoritative state machine. Quality and UX criteria compile into ordinary lifecycle controls. Production adapters verify externally signed observations before they enter the evidence protocol. Outcome realization and continuing justification form a mandatory feedback loop between intent, operations, and governance. The earlier A1–A8 graph remains a compatibility projection for the strict engineering loop; it is not expected to encode the entire production lifecycle. See `ONBOARDING_AND_VISUAL_OPERATOR.md`, `PRECONFIGURED_PRODUCTION_ADAPTERS.md`, `UX_ENGINEERING_PROFILE.md`, `SOFTWARE_QUALITY_PROFILE.md`, and `OPERATOR_GUIDE.md`.

## Conversational facilitation boundary

The guided operator composes existing services rather than replacing them. Its persisted journey contains intake state and references to review packets. Its status view is derived from authoritative lifecycle state. A consolidated packet may contain multiple decisions for one principal, but each item preserves a distinct scope, evidence basis, exact challenge, and replay state.

The lifecycle copilot sits above, not inside, the authority boundary. It authenticates a local human principal by key possession, creates an expiring session, signs dialogue as non-authoritative, optionally invokes a read-only external facilitator, and prepares structured mandate or authorization decisions. Only an exact decision challenge from the required human principal can ask the control plane to apply an effect. The copilot cannot mint an arbitrary scope: authorization packets must correspond to an active build, release, or current specification-change gate.

```text
human principal <-> lifecycle copilot -> decision proposal
       |                                    |
       +------ exact authenticated decision +
                                            v
                              authoritative CLSES engine
                                            |
                  agent / build / deployment / observation workers
```

The rebuilt system has one authoritative state model. Every meaningful transition creates an immutable, content-addressed, actor-signed record and appends its digest to a hash-chained ledger. Mutable references only identify the current immutable record.

An external-agent adapter adds bounded autonomous engineering. The human-signed mandate fixes the objective, driver, specification digest, allowed path patterns, allowed criteria, expiry, and iteration/change/byte budgets. External agents operate on a temporary view and return structured proposals. They never receive a signing role.

## Normative artifacts

| Type | Meaning | Canonical source |
|---|---|---|
| A1 | Purpose and outcomes | Accepted signed specification |
| A2 | Requirements and constraints | Accepted signed specification |
| A3 | Design and interfaces | Accepted signed specification |
| A4 | Authorized engineering work | Exact change-set build grant |
| A5 | Built and deployed implementation | Build and deployment records |
| A6 | Evaluation method | Criterion bindings from the specification |
| A7 | Observation | Signed test and operational records |
| A8 | Decisions and authority | Signed engineering and production grants |

The manifest is a deterministic projection of the same accepted graph. It is never a parallel manually maintained source of truth.

## Control flow

```text
signed specification
        ↓
human autonomy mandate → external agent ↔ signed trial evidence
        ↓                         ↑ failed trial
traced work request → bounded authorization → signed agent execution
        ↓
canonical change set → exact build authorization → tests + artifact
        ↓
artifact acceptance → separate deployment authorization
        ↓
verified deployment → operational observation
        ↓
A1–A8 projection → intrinsic validation → bounded relational verdict
        ↓
signed cycle closure and accepted baseline
```

Any mismatch stops the transition. There is no permissive fallback.

Autonomy stops at authority boundaries. The engineering reviewer must authorize the exact final change set; the release owner must separately accept the artifact and authorize deployment. Resuming the durable run after those decisions continues orchestration without transferring the authority role to the agent.

## Trust boundary

The reference implementation uses protected local HMAC keys and a local deployment adapter. It detects ordinary record, graph, artifact, and ledger tampering relative to that local trust root. A host administrator can still replace keys, code, or the runtime. Production adapters must supply managed identities, protected CI runners, immutable external logs, protected environments, and independent telemetry.
