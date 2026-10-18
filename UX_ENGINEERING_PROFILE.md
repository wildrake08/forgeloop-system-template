# Composable UX Engineering Profile

CLSES 4.4 adds `ux-engineering`, an optional quality-profile overlay for interactive software. It extends—not replaces—`software-quality`: every software-quality dimension and criterion remains active, and UX-specific controls are added by composition. The packaged point-of-sale and SaaS lifecycle profiles opt into the overlay.

The profile is an executable assurance contract, not a style guide and not a universal usability or accessibility certification. Human authorities still declare consequential thresholds for the named system and context.

## UX dimensions and criteria

| Dimension | Criteria |
|---|---|
| Research grounding | Critical-user-segment research coverage; material operating-context validation |
| Task effectiveness | Critical-journey success; error-free completion |
| Efficiency and cognitive load | Time on task; cognitive-load instrument score |
| Learnability | First-use success; time to proficiency |
| Error tolerance and recovery | Preventable-error rate; error-recovery success |
| Information architecture | Findability; navigation dead ends |
| Trust, transparency, and control | Consequential-choice comprehension; user-control coverage |
| Satisfaction and continuity | Post-task satisfaction; journey abandonment |
| Inclusion and contextual fit | Assistive-technology task success; localized-journey success |
| Ethical and AI interaction | Deceptive-pattern count; AI-decision understanding; AI recourse success |

Together, the composed profile contains nineteen dimensions and thirty-nine criteria: nine dimensions/eighteen criteria from software quality plus ten dimensions/twenty-one criteria from UX engineering.

## Evidence scope

A UX conclusion is valid only for its declared scope. The `CLSES-ux-assessment/v1` envelope contains the complete ordinary quality assessment and adds:

- named user populations;
- named critical journeys;
- named operating contexts;
- declared measurement instruments;
- one scope binding for every applicable UX criterion;
- sample size and the exact evidence digest for each binding; and
- a human-approved research-ethics record covering consent, privacy review, and recruitment limitations.

Every applicable UX scope must bind to a current passing observation. Claimed populations, journeys, operating contexts, and instruments must be subsets of the assessment declarations. Instrument-score criteria require a declared instrument. Missing, duplicate, foreign, or digest-mismatched scope bindings fail closed.

## Applicability

Most foundational UX criteria always apply when the UX profile is selected. Contextual controls activate only when relevant:

- `frequent_use`, `professional_user`, or `training_required` activates time-to-proficiency;
- `production_users` or `instrumented_experience` activates journey-abandonment evidence;
- `user_interface`, `public_facing`, or `accessibility_required` activates assistive-technology task testing;
- `localized` or `multilingual` activates localized-journey testing; and
- `ai_mediated` or `automated_decision` activates AI understanding and recourse.

The underlying software-quality criteria retain their own applicability rules. Every criterion receives an explicit disposition; required criteria cannot be silently excluded.

## Authority and thresholds

The profile specifies metric meaning, unit, comparison direction, evidence type, authority role, evidence age, applicability, and change triggers. It deliberately does not choose numeric acceptance thresholds. The appropriate human authority must declare each threshold for the actual users, journeys, risk, context, and named measurement instrument.

Trade-offs remain named, criterion-bound, human-authorized, and review-dated. A UX trade-off cannot waive applicable safety, accessibility, consent, or authority constraints.

## Commands

Inspect applicable criteria and change impact:

```sh
clses-ux applicable \
  --context-tag user_interface \
  --context-tag production_users \
  --context-tag localized

clses-ux affected --change-kind user_population
```

Assess a scoped UX evidence package:

```sh
clses-ux assess ux-assessment.json
```

A positive result means the composed software-quality and UX criteria pass for the declared system, users, journeys, operating contexts, environment, instruments, thresholds, evidence, ethics record, and evidence window. Material changes select affected criteria through their declared triggers and require reassessment before the assurance conclusion can be renewed.

## Use from another lifecycle profile

Extend the lifecycle profile:

```json
{"extends": ["ux-engineering"]}
```

Select `ux-engineering` for quality/UX assessment. Profile composition rejects duplicate dimensions or criteria and lifecycle binding verification rejects any disagreement in evidence type, authority role, or evidence age.
