---
name: scaffold-docs-governance
description: Use this skill when the user asks to set up project documentation — README, CONTRIBUTING, CHANGELOG, SECURITY, LICENSE, ADRs, or governance files. Covers Phase 7 of the engineering Quickstart.
---

# Scaffold Docs & Governance (Fase 7)

Creates the canonical documentation set for any professional Python repository.

## When to use

- "Criar README"
- "Setup CONTRIBUTING"
- "CHANGELOG"
- "SECURITY.md"
- "ADRs"

## Pre-flight (ask the user)

1. **Project description** (1 paragraph, the "what + why").
2. **License** (default `MIT`, alternatives: `Apache-2.0`, `proprietary`).
3. **Security contact email** (for `SECURITY.md`).
4. **Maintainer GitHub handle(s)** (for `CODEOWNERS` if not already set).

## Files to create

### 1. `README.md` — must answer in 30 seconds

```markdown
# <Project>

<one-line tagline>

## What it does

<one paragraph>

## Quickstart

\```bash
git clone <repo>
cd <repo>
make setup        # installs deps + git hooks
make test         # runs the test suite
make run          # starts the app (if applicable)
\```

## Documentation

- [Contributing](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/)
- [Changelog](CHANGELOG.md)

## License

<License name> — see [LICENSE](LICENSE).
```

**Test:** a new developer reads only the README and can run the project in < 5 min. If not, README is incomplete.

### 2. `CONTRIBUTING.md`

```markdown
# Contributing

## Setup

\`\`\`bash
git clone <repo> && cd <repo>
make setup
\`\`\`

## Workflow

1. Branch from `main`: `git checkout -b feat/description`
2. Small commits with Conventional Commits format
3. `make all` must be green before push
4. Open PR against `main`
5. Wait for CI green + review

## Commit types

`feat` | `fix` | `test` | `docs` | `chore` | `refactor` | `perf` | `ci` | `build` | `style` | `revert`

## Branch naming

`feat/` `fix/` `chore/` `refactor/` `test/` `docs/` `ci/` `hotfix/` `release/`

## Tests

- Unit: `make test` (threshold: 80%)
- Integration: `make test-integration`
```

### 3. `CHANGELOG.md`

Keep a Changelog format. Start with:

```markdown
# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding.
```

### 4. `SECURITY.md`

```markdown
# Security Policy

## Reporting a Vulnerability

Send details to **<security-email>**.
Do **not** open public issues for vulnerabilities.

- **Initial response:** 48 business hours
- **Triage:** 5 business days
- **Coordinated disclosure:** 90 days after fix

## Supported Versions

| Version | Supported |
|---------|----------|
| latest  | ✅        |
| < 1.0   | ❌ (EOL)  |
```

### 5. `LICENSE`

Use the SPDX-standard text for the chosen license. For `MIT` use the template at https://opensource.org/licenses/MIT.

### 6. `docs/adr/template.md`

```markdown
# ADR-XXXX: [Short decision title]

- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-YYYY
- **Date:** YYYY-MM-DD
- **Deciders:** [@user1]

## Context

What problem are we solving? What constraints exist?

## Decision

What we decided.

## Alternatives Considered

- **Option A** — discarded because ...
- **Option B** — discarded because ...

## Consequences

### Positive
- ...

### Negative / Trade-offs
- ...
```

Create the first ADR at `docs/adr/0001-use-uv-as-package-manager.md`.

### 7. `.env.example`

If not yet created (should be from `scaffold-python-repo`), populate with all env vars used by the app, with placeholder values.

### 8. `.github/PULL_REQUEST_TEMPLATE.md` and `.github/CODEOWNERS`

Should already exist from `scaffold-ci-cd`. Verify and update if needed.

## Validation

```bash
# README quickstart actually works
git clone <repo> /tmp/test-readme && cd /tmp/test-readme && make setup && make test
```

If the README's commands don't produce a green build, fix the README, not the commands.

## Commit

```bash
git add README.md CONTRIBUTING.md CHANGELOG.md SECURITY.md LICENSE docs/
git commit -m "docs: add canonical docs (README, CONTRIBUTING, CHANGELOG, SECURITY, ADR)"
```

## Hand-off

Recommend `audit-repo-health` to verify everything is in order.
