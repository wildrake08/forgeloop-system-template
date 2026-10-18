# Onboarding, Discovery, and Visual Operation

CLSES 4.5 adds one easier front door without changing the assurance or authority model.

## Onboarding templates

Three packaged templates cover coffee-cart point of sale, SaaS web applications, and general interactive software. A template selects the composed lifecycle profile, supplies only non-consequential starter classification, and describes the smallest human inputs needed for a viable baseline.

```sh
clses-operator templates
clses-operator onboard-plan --template coffee-cart-pos --answers answers.json
clses-operator --root ./coffee-pos onboard --template coffee-cart-pos --answers answers.json
```

The plan is `none` in authority effect. Applying it creates the controlled workspace and begins intake; it does not approve the baseline or any engineering, build, release, or deployment action. The target must satisfy the kernel's empty-repository initialization rule.

## Read-only discovery

```sh
clses-operator --root ./new-system discover --output discovery.json
```

Discovery examines only local file/directory indicators, file hashes, platform identity, runtime presence, and the presence—not values—of a small allowlist of environment keys. It never contacts external services. Its digest-bound suggestions are `proposed_not_authorized`. They enter onboarding only when the operator supplies both the report and `--accept-discovery`; explicit onboarding answers take precedence.

## Visual operator

```sh
clses-operator --root ./new-system serve
# or: clses-operator-ui --root ./new-system
```

Open the printed loopback URL. The visual interface supports discovery, template planning and application, remaining intake answers, status, human session opening, agent registration, mandate preparation, consolidated authorization review, exact individual decisions, run continuation, and production-adapter visibility.

The server binds only to loopback, requires a per-process CSRF token for every mutation, applies restrictive browser headers, limits request bodies, does not log requests or credentials, and delegates every lifecycle action to the same guided operator and control plane used by the command interface.

Session bearer tokens remain in browser memory. The reference local credential model is not a production identity provider. Organizations should place an authenticated, TLS-protected interface in front of the same APIs when remote access is required.
