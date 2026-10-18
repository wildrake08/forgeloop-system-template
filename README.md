# CLSES GitHub Template Edition v4.6.1

This directory is a safe, self-contained GitHub **Use this template** repository for starting a governed software system. Version 4.6 adds exact scaffold adoption, a digest-bound embedded kernel, least-privilege CI with immutable action references, starter source/tests, GitHub contribution surfaces, secret exclusions, dependency hashes, and copied-repository tests. Start with `GITHUB_TEMPLATE_GUIDE.md`.

This is a complete architectural rebuild around a general assurance kernel, composable lifecycle profiles, and replaceable adapters. It retains the lifecycle copilot, bounded autonomous engineering, signed record control plane, A1–A8 compatibility projection, and production evidence gate. The copilot cannot infer approval or sign as a human.

The base production profile governs sixteen domains from intent and outcome realization through retirement. Point-of-sale and SaaS overlays demonstrate how system-specific obligations are added without weakening the base. The `clses-assure` verifier issues a time-bounded verdict only when lifecycle coverage, required trace relationships, adapter provenance, control-specific evidence, independently authorized continuation, current deployed bytes, change reassessment, and closure all agree.

Version 4 adds end-to-end assurance of the “why.” Need, beneficiaries, alternatives, intervention logic, measurable outcome hypotheses, benefit-risk, economics, ethical effects, realized benefit, and continuing justification are normative controls. A positive verdict requires production-grounded outcomes to meet their targets for multiple declared periods, with a baseline, counterfactual, attribution method, acceptable costs and harms, valid assumptions, and a review-dated decision from an independent outcome authority. See `OUTCOME_ASSURANCE.md`.

Version 4.1 adds `clses-intake`, a normative minimal-viability engagement engine. It derives required facts from the composed profile, reuses supplied context, selects only safe reversible defaults, defers premature technical choices, maintains an expiring assumption registry, deduplicates questions, batches the irreducible gaps, and produces one non-authoritative baseline proposal. For the point-of-sale profile, an empty context requires five consolidated question groups; complete context requires none. See `MINIMAL_VIABILITY_INTAKE.md`.

Version 4.2 introduced `clses-operator`, a thin guided operator journey over intake, the copilot, autonomous execution, and the control plane. The current release supplies one seven-step workflow, one plain-language status response, deterministic conversational turns, and consolidated authorization review packets. Consolidation is presentational only: product intent, engineering, acceptance, and deployment remain separate exact decisions assigned to the required authenticated human principal. See `OPERATOR_GUIDE.md`.

Version 4.3 adds the composable `software-quality` lifecycle profile and `clses-quality` assessment interface. Nine dimensions and eighteen criteria carry explicit metrics, units, comparison operators, evidence types, authority roles, freshness limits, context applicability, trade-off governance, and change triggers. Consequential thresholds remain system-specific human decisions. The point-of-sale and SaaS profiles now include these quality controls by composition. See `SOFTWARE_QUALITY_PROFILE.md`.

Version 4.4 adds the composable `ux-engineering` profile and `clses-ux` assessment interface. It extends software quality with ten UX dimensions and twenty-one criteria covering research grounding, effectiveness, efficiency, cognitive load, learnability, error recovery, information architecture, trust and control, satisfaction, inclusion, localization, ethical interaction, and AI recourse. UX observations are bound to named populations, journeys, operating contexts, instruments, samples, research-ethics approval, and evidence digests. Point-of-sale and SaaS now opt into UX engineering by composition. See `UX_ENGINEERING_PROFILE.md`.

Version 4.5 adds three guided onboarding templates, read-only secret-safe environment discovery, a loopback-only visual operator, and six preconfigured signed production-evidence adapter families. These conveniences reuse the existing control plane: discovery and templates remain non-authoritative, browser mutations require CSRF protection, exact decisions remain separate, and production observations require an external public-key trust anchor and exact request binding. See `ONBOARDING_AND_VISUAL_OPERATOR.md` and `PRECONFIGURED_PRODUCTION_ADAPTERS.md`.

Version 4.6 makes that system usable as a GitHub template without weakening empty-repository initialization. A copied non-empty repository is adopted only through its exact release manifest; ordinary non-empty directories are still refused.

Version 4.6.1 is the corrective release informed by a real coffee-cart POS cycle. It inserts an exact owner-signed product-baseline gate before engineering, replaces deferred architecture and language assumptions with execution evidence, reports a closed cycle as fully completed with monitoring active, includes trial transcripts and digests in build review packets, returns actionable external-agent failures, safely ignores only an allowlist of local development artifacts during scaffold adoption, and requires two distinct passing outcome periods for a production verdict.

Run `/opt/homebrew/bin/python3 build.py` (or another Python 3.10+ environment with the declared dependencies) to execute the full suite and live governed lifecycle, issue signed package evidence, and replay the independent verification. Distribution checksums remain the release-package trust anchor; the public key embedded in the assessment proves internal integrity but not publisher identity. See `COPILOT_GUIDE.md` for the conversational workflow and `PRODUCTION_PROFILE.md` for target-environment verification.

This is a clean rebuild of the end-to-end closed-loop software engineering reference. It combines strict spec-driven development with authorized agent execution, but also governs build, evidence, acceptance, release, deployment, operation, assessment, and change-triggered repetition.

## Guided operation

For the simplest supported experience, use only `clses-operator`:

```sh
clses-operator --root ./my-system setup --system-id my-system
clses-operator --root ./my-system begin --profile point-of-sale
clses-operator --root ./my-system status
```

The same surface opens human sessions, prepares mandates, groups currently actionable authorization requests, applies exact decisions, and continues authorized runs. It does not hide uncertainty or infer approval.

For the local visual workflow:

```sh
clses-operator --root ./my-system serve
```

## Lifecycle Copilot

`clses-copilot` provides signed, lifecycle-aware conversation. An owner may register Codex or a generic advisory facilitator; its read-only response can explain evidence and suggest one next action but has no authority. Human sessions require possession of the local principal credential, expire, and issue a one-time bearer token. Conversation remains non-authoritative. Mandates and active lifecycle scopes become effective only through a separate, exact, non-replayable approve or reject challenge. Specification changes, autonomous runs, build approval, artifact acceptance, deployment authorization, closure, and reassessment remain enforced by the underlying control plane.

## Autonomous engineering with Codex

Register the built-in non-interactive Codex adapter, then have a human engineering authority issue a bounded mandate:

```sh
clses-v1 --root ./my-system driver-register --name codex --kind codex

clses-v1 --root ./my-system mandate \
  --run-id feature-17 \
  --objective "Implement the declared receipt behavior and make its tests pass" \
  --driver codex \
  --allowed-path 'src/service.py' \
  --allowed-path 'tests/*' \
  --requirement test_pass_rate \
  --max-iterations 5 --max-changes 12 --max-bytes 50000

clses-v1 --root ./my-system autonomy-run --run-id feature-17
```

The external agent sees an isolated copy, the signed specification, budgets, and prior trial evidence. It returns schema-constrained proposals; it does not edit the governed repository directly. The orchestrator applies valid proposals as signed agent executions and repeats tests until success, a block, or budget exhaustion.

When tests pass, the run stops and reports an exact `build:<digest>` scope. A non-agent engineering reviewer must authorize it. A resumed run builds and stops again for the two non-autonomous `accept:<digest>` and `deploy:<digest>` gates. After those approvals, another resume completes deployment, observation, assessment, and closure.

The Codex adapter follows the documented non-interactive `codex exec` pattern with a read-only sandbox, an output schema, an output file, and an ephemeral session. See https://learn.chatgpt.com/docs/non-interactive-mode.

## Other external agents, including Claude Code

Register a vendor CLI or organization-controlled wrapper as a generic argv array. It must accept the substituted `{prompt}` and return the protocol JSON on stdout, or write it to `{output}` when that placeholder is included.

```sh
clses-v1 --root ./my-system driver-register \
  --name organization-agent --kind generic \
  --argv-json '["/opt/agents/run-engineer","--prompt","{prompt}","--context","{context}","--output","{output}"]'
```

This interface is vendor-neutral. A Claude Code wrapper can be registered the same way without granting it specification acceptance, signing, artifact acceptance, or deployment authority.

## Start in an empty repository

```sh
clses-v1 --root ./my-system init \
  --system-id my-system \
  --purpose "Provide a reliable service" \
  --beneficiary users
```

Create and approve a traced change:

```sh
clses-v1 --root ./my-system request \
  --work-id behavior-1 \
  --instruction "Add the reviewed behavior" \
  --path tests/test_behavior.py \
  --content 'import unittest' \
  --requirement test_pass_rate

clses-v1 --root ./my-system authorize \
  --scope work:behavior-1 --kind engineering \
  --signer engineering-reviewer --subject agent
clses-v1 --root ./my-system execute --work-id behavior-1
clses-v1 --root ./my-system plan
```

Authorize the exact `build:<change-set-digest>` returned by `plan`, then run `build`. Authorize both exact scopes returned by `build`—`accept:<artifact-digest>` and `deploy:<artifact-digest>`—using `release-owner` for `operator`. Run `complete`, then `verify`.

```sh
clses-v1 --root ./my-system verify
```

Direct edits, unknown or stale traces, wrong actors, absent approvals, failed tests, changed build inputs, modified artifacts, unhealthy observations, inconsistent A1–A8 graphs, and stale baselines fail closed.

The local cycle deliberately reports `locally_demonstrated_not_production_adequacy`. A production verdict is available only through `clses-production-verify`, with an externally supplied trusted public key and authentic target-environment evidence. It requires exact component/artifact/deployment equality, criterion-specific fresh observations, at least two ordered and independently evidenced passing periods for every declared outcome, acceptance and deployment decisions, complete change monitors, supply-chain controls, recovery exercises, operations telemetry, and closure. Any changed deployed byte, expired evidence, missing period, reused period evidence, or failed outcome invalidates the verdict.

## Governed specification change

```sh
clses-v1 --root ./my-system spec-propose --change-id spec-2 --spec next-spec.json
```

Approve the returned `spec:<change-id>` engineering scope and `spec-accept:<digest>` acceptance scope, then run `spec-apply`. A new cycle is required before the system is again current.

## Verify the package

```sh
python -m unittest discover -s kernel_tests -v
python build.py
python -m clses_mvas_v1.release_assessment verify
```

The release assessment separately evaluates twenty-three package parts, including onboarding and discovery, the visual operator, preconfigured production adapters, the guided operator, software-quality profile, and UX Engineering Profile. It also validates minimal-viability intake, purpose and outcome assurance, the general kernel, adapter protocol, integrated engineering system, and production evidence gate. It binds evidence to the current source inventory and normative contracts and signs the complete evidence object with a one-time RSA-SHA256 release key. Verification fails if a packaged source, test, schema, profile, document, manifest, verdict, or signature changes.

Intrinsic conformance means the schemas, artifacts, references, transitions, authorization rules, evidence bindings, and integrated graph are internally valid. The package is an adequate production-evidence-gated framework. No unevaluated system is declared adequate: production relational adequacy is bounded to the signed specification, exact environment, current deployed bytes, evidence methods, and evidence expiry.
