# GitHub “Use this template” guide

## Publish the template repository

Upload this release directory as the repository root. In GitHub repository settings, enable **Template repository**. Protect the default branch with a ruleset that requires the `verify` job, pull-request review, conversation resolution, and blocked force pushes/deletions. Configure actual owners in `.github/CODEOWNERS`; the shipped comments deliberately grant nobody authority.

GitHub settings and organization identities are external controls and cannot be carried by a repository copy. Apply them before treating the repository as production-governed.

## Create and initialize a software-system repository

1. Select **Use this template** and create a new repository.
2. Clone the new repository without changing any copied file.
3. Prefer an environment outside the repository, for example `python3 -m venv ../YOUR-SYSTEM-runtime`, activate it, and install this local package with `python -m pip install .`. Editable installs are also supported.
4. Adopt the exact released scaffold:

   `python -m clses_mvas_v1.template_edition --root . bootstrap --system-id YOUR-SYSTEM --purpose "YOUR PURPOSE" --beneficiary "YOUR BENEFICIARY" --github-owner @YOUR-ORG/YOUR-TEAM`

5. Run `python -m clses_mvas_v1.template_edition --root . check` and `python -m unittest discover -s tests -v`.
6. Keep `.clses-v1/` local and protected. Do not commit its credentials.
7. Use `clses-operator --root . begin --profile base-production` for guided intake, or select `point-of-sale` / `saas` as applicable.

Initialization is deliberately one-shot. It fails if any released file was changed, deleted, linked, or unexpectedly added before adoption. Only after that exact check does it write the validated `@user` or `@organization/team` owner into `CODEOWNERS`; the resulting file digest is bound into the signed baseline. A fixed allowlist excludes Git metadata, `.clses-v1/`, Python caches, `.venv`/`venv`, `build`/`dist`, coverage and tool caches, `.DS_Store`, and top-level `*.egg-info`; entries outside that list—including symbolic links—still fail closed. The manifest includes the signed release assessment. After adoption, application changes are allowed only through the governed lifecycle; embedded kernel and governance files remain digest-bound.

## What is and is not automatic

The template supplies the starter application, complete kernel, onboarding, profiles, adapters, CI, issue/PR forms, dependency pinning, security guidance, and fail-closed adoption. It does not infer human decisions, create production credentials, configure repository rulesets, establish an identity provider, or claim that a new application is production-adequate. Those become valid only from explicit authority and authentic system/environment evidence.
