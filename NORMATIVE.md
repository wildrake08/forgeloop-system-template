# Normative Contract

## CLSES 4.5 governing layer

The v4.5 onboarding template, onboarding plan, and environment-discovery envelopes are normative. A template MUST NOT supply consequential authority or acceptance decisions. Discovery MUST be local and read-only, MUST NOT expose environment-variable values, and MUST label all suggestions `proposed_not_authorized`. A discovery report MUST be digest-valid and MUST NOT enter intake without an explicit acceptance action. Onboarding answers MUST be limited to fields declared by the selected template, and applying a plan MUST retain the baseline as non-authoritative.

The visual operator MUST bind only to loopback in the reference implementation, require its session-specific CSRF token for every mutation, and delegate all effects to existing governed services. It MUST NOT convert conversation, UI actions, packet grouping, or agent actions into authority. Each consequential decision MUST retain its exact scope, authenticated principal, challenge, and separate outcome.

The v4.5 production-observation envelope and preconfigured adapter protocol are normative. An instantiated adapter MUST bind to an external public-key digest. Every imported observation MUST have a valid detached signature, match the exact request system, environment, artifact, and evidence type, be passing and current, expire no later than the request, and contain measurements. Private keys MUST NOT be packaged. Key substitution, signature failure, stale or failing evidence, request rebinding, and undeclared capability MUST fail closed.

The v4.1 intake state and minimum viable baseline are normative envelopes. An intake question MAY be emitted only when its fact is required by a composed-profile control, material, not reliably derivable, and unsafe to defer. Consequential facts MUST NOT receive defaults. Defaults MUST be reversible, registered as expiring assumptions, and reevaluated on expiry. The generated baseline MUST remain `proposed_not_authorized` until accepted through the authority plane.

The v4.2 guided operator state and authorization request packet are normative envelopes. A status view MUST be derived from current intake and lifecycle state. A review packet MUST contain only currently active scopes assigned to its authenticated principal. Consolidation MUST NOT merge decisions: every item retains an exact scope, evidence basis, required principal, one-time challenge, and independent outcome. Conversational language, silence, packet preparation, and packet inspection MUST have no authority effect.

The v4.3 software-quality profile and quality-assessment envelope are normative. Every packaged criterion MUST bind to exactly one lifecycle quality control with the same evidence type, authority role, and maximum evidence age. Every criterion MUST receive an explicit applicability disposition. Required criteria MUST NOT be excluded. Applicable criteria MUST have authority-declared thresholds and fresh metric-, unit-, environment-, and profile-bound observations. Accepted trade-offs MUST be named, authority-owned, criterion-bound, and review-dated. The profile MUST NOT invent consequential threshold defaults.

The v4.5 UX Engineering Profile and UX-assessment envelope are normative when `ux-engineering` is selected. The profile MUST extend `software-quality` without removing or weakening inherited criteria. Every applicable UX criterion MUST have exactly one scope binding to its current observation and evidence digest. Its claimed populations, critical journeys, operating contexts, and instruments MUST be declared by the assessment. Instrument-score criteria MUST name a declared instrument. The sample size MUST be positive. Research ethics MUST record consent basis, privacy review, recruitment limitations, human approver, and approval time no later than assessment. Missing, duplicate, foreign, stale, or mismatched bindings MUST fail closed. UX change triggers MUST reopen affected criteria.

For general production engineering, the normative governing objects are the lifecycle profile, adapter manifest/request/result envelopes, and assurance dossier defined by the v4 schemas and `clses_mvas_v1.assurance`. A conformant dossier MUST cover every composed profile domain and control, MUST realize every required lifecycle edge, MUST bind fresh passing evidence to an immutable adapter identity and exact artifact/environment, MUST bind one non-agent authority decision to all evidence for each control, MUST reconcile release paths with the current deployment, MUST demonstrate that every declared beneficiary outcome is achieved across its minimum sustained periods, MUST bind outcome claims to baselines, counterfactuals, attribution, costs, harms, and assumptions, MUST obtain an independent review-dated continuation decision, MUST reassess every affected control after material change, and MUST close over the exact decision set and continuation action before evidence expiry.

The A1–A8 contract below remains normative for the strict engineering-loop compatibility projection. It is a component of the v4 governing model, not the complete general lifecycle ontology.

The JSON Schemas under `clses_mvas_v1/schemas` define the structural contract for the manifest envelope and A1–A8 payloads. `clses_mvas_v1.validator` defines the executable cross-artifact contract.

The system shall reject a manifest when any of these invariant families fail:

1. Identity: unique `(id, version)`, immutable type and subject, contiguous revisions, exact supersession.
2. Reference integrity: every reference resolves, typed references are explicit edges, allowed direction is respected, and the graph is acyclic.
3. Ownership: requirements belong to purpose, designs cover active requirements, work and implementation bind active design, and evidence binds implementation plus method.
4. Authorization: engineering and production grants have the required kind, actor, scope, subject, time window, and revocation state.
5. Lifecycle: work and decisions follow permitted monotonic transitions; observations are append-only.
6. Evidence: criterion bindings, units, provenance, source count, coverage, freshness, horizon, and target are consistent.
7. Closure: verified closure uses passing, post-finding, pre-closure evidence; failure cannot establish closure.
8. Completeness: every active criterion has an evaluation method and observation, every deployed implementation has evidence, and every A1–A8 type is present.

The operational engine adds mandatory signed specification control, unique work identities, declared-component enforcement, agent-only writes, exact change-set build approval, complete source artifact binding, distinct acceptance and deployment gates, verified observation, signed cycle closure, and reassessment after change.

An autonomy mandate is a non-autonomous engineering decision. It must bind one immutable run identity, external driver, objective, current specification digest, path and criterion allowlists, expiry, and positive iteration/change/byte budgets. It authorizes only engineering proposals, bounded execution, and trial testing. It never authorizes specification application, release-grade build approval, artifact acceptance, deployment, risk acceptance, or closure.

Intrinsic conformance does not by itself establish relational adequacy. A positive relational verdict requires authentic observations from the declared operating conditions and must retain its claim boundary.
