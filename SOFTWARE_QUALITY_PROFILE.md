# Composable Software Quality Profile

CLSES 4.3 adds an executable quality model that composes with the base production, point-of-sale, SaaS, and UX Engineering lifecycle profiles. It is influenced by widely used software-product quality concepts but is an independent CLSES contract, not a claim of certification to any external standard.

## Dimensions

| Dimension | Packaged criteria |
|---|---|
| Functional suitability | Functional completeness; functional correctness |
| Performance efficiency | Response time; capacity |
| Compatibility | Interface conformance; coexistence |
| Interaction capability | Operability; accessibility |
| Reliability | Availability; recoverability |
| Security | Integrity; confidentiality |
| Maintainability | Analyzability; testability |
| Flexibility | Adaptability; replaceability |
| Safety | Fail-safe behavior; hazard control |

Every criterion declares its metric, unit, comparison operator, evidence type, authority role, maximum evidence age, applicability rule, context tags, and change triggers. The matching lifecycle overlay binds each criterion to an assurance control. Package verification fails if the quality catalog and lifecycle controls disagree.

## No universal threshold defaults

The profile does not silently decide what “good enough” means. Each applicable criterion needs a numeric threshold explicitly declared by its responsible human authority for the named system, workload, environment, users, and risk context. For example, the profile declares `p95_response_time`, milliseconds, and `<=`; the product or quality authority declares the acceptable number.

This separates reusable measurement semantics from consequential acceptance policy.

## Applicability and tailoring

Core criteria are always applicable. Contextual criteria activate from declared tags such as:

- `user_interface` or `public_facing`
- `personal_data`, `confidential_data`, or `regulated_data`
- `persistent_state` or `critical_service`
- `high_load`, `scalable`, `shared_environment`, or `multi_tenant`
- `external_dependency` or `replaceable_adapter`
- `safety_relevant`

Every criterion still receives an explicit disposition. A required criterion cannot be excluded. A contextual exclusion must retain a rationale and responsible authority. Applicability is deterministic and testable:

```sh
clses-quality applicable \
  --context-tag user_interface \
  --context-tag personal_data \
  --context-tag persistent_state
```

## Assessment

An assessment binds:

- the exact composed quality-profile digest;
- system, environment, and context tags;
- one authority decision for every criterion;
- explicit thresholds for applicable criteria;
- metric- and unit-matched observations;
- evidence digests, observation times, and expiration times;
- governed, review-dated trade-offs.

Run:

```sh
clses-quality assess quality-assessment.json
```

A positive result means the declared quality criteria passed for the named context, environment, thresholds, observations, trade-offs, and evidence window. It is not a universal or permanent quality certification.

## Trade-offs

Quality dimensions can conflict. A trade-off—such as accepting additional response time to preserve offline durability—must name its affected criteria, decision, rationale, human authority, decision time, and review date. It must also be referenced from every affected criterion decision. Unbound or expired trade-offs fail assessment.

## Change-triggered reassessment

Each criterion declares change kinds that invalidate or reopen its conclusion. For example, a dependency change affects response time, integrity, confidentiality, and replaceability, but not necessarily operability. Determine the exact affected set with:

```sh
clses-quality affected --change-kind dependency
```

Fresh measurements and authority decisions are then required only for affected controls, subject to the broader lifecycle profile and actual impact analysis.

## Composition

The `software-quality` lifecycle profile extends `base-production`. The `ux-engineering` profile extends `software-quality`, and the packaged `point-of-sale` and `saas` profiles extend `ux-engineering`. Each layer adds controls without weakening its parents. The separate quality catalog and assessment schema remain reusable by future system-class overlays. See `UX_ENGINEERING_PROFILE.md` for the UX-specific evidence-scope contract.
