---
name: audit-repo-health
description: Use this skill when the user asks to audit, review, or verify a repository against the engineering best practices — checks tooling, CI, tests, docs, security, and produces a gap report with prioritized fixes.
---

# Audit Repo Health

Systematic read-only audit of a Python repo against professional engineering standards. Produces a gap report with prioritized fixes.

## When to use

- "Audita este repo"
- "Está conforme as best practices?"
- "Health check"
- "Onboarding a new project"

## How to run

This is a **read-only** skill by default. Only modify files when the user explicitly asks for fixes after seeing the report.

## Audit dimensions (15 checks from §1 of best-practices)

For each check, output: **PASS / FAIL / N/A** + short evidence + suggested fix.

### 1. Reproducibility
- [ ] `git clone && make setup && make test` works on a clean machine.
- Evidence: `Makefile` exists with `setup` target; `uv.lock` present.

### 2. Lockfile committed
- [ ] `uv.lock` is tracked by git and in sync with `pyproject.toml`.
- Check: `git ls-files uv.lock` non-empty + `uv sync --frozen` succeeds.

### 3. Pre-commit active
- [ ] `.pre-commit-config.yaml` exists.
- [ ] Hooks include: ruff (lint + format), mypy, gitleaks or detect-private-key.
- [ ] `make setup` installs hooks (`pre-commit install`).

### 4. CI blocks bad merges
- [ ] `.github/workflows/ci.yml` exists.
- [ ] Workflow runs on `pull_request`.
- [ ] Branch protection on `main` requires status checks (verify via `gh api repos/.../branches/main/protection` if possible).

### 5. No secrets in git
- [ ] `.env` is in `.gitignore`.
- [ ] Run `gitleaks detect` — must return 0 findings.
- [ ] `git log -p -- '*.env'` empty.

### 6. Conventional Commits enforced
- [ ] `.githooks/commit-msg` exists.
- [ ] Recent commit log follows the format: `git log -20 --pretty=%s | grep -vE '^(feat|fix|docs|chore|refactor|test|perf|ci|build|style|revert)(\(.+\))?(!)?: '` returns empty.

### 7. Test coverage ≥ 80%
- [ ] `pyproject.toml` has `[tool.coverage.report] fail_under = 80`.
- [ ] CI runs `pytest --cov-fail-under=80`.
- [ ] Run `make test` — coverage actually meets it.

### 8. Strict type checking
- [ ] `pyproject.toml` has `[tool.mypy] strict = true`.
- [ ] Run `uv run mypy .` — must pass with 0 errors.

### 9. Docker non-root
- [ ] If `Dockerfile` exists, production stage has `USER appuser` (or equivalent non-root).
- [ ] `HEALTHCHECK` instruction present.

### 10. Dependency auditing
- [ ] `.github/dependabot.yml` exists.
- [ ] CI runs `pip-audit` (or `safety`).
- [ ] `deptry .` reports 0 unused/missing deps.

### 11. Env vars validated
- [ ] Search `src/` for `pydantic_settings` or equivalent.
- [ ] `os.getenv` grep in `src/` returns ≤ 0 occurrences (allowed only in `settings.py`).

### 12. Structured logging
- [ ] `print(` in `src/` returns 0 occurrences.
- [ ] `structlog` or equivalent JSON logger is configured.

### 13. README answers in 30s
- [ ] `README.md` exists.
- [ ] Contains: project description, quickstart commands, link to CONTRIBUTING.
- [ ] Quickstart commands actually run.

### 14. CHANGELOG maintained
- [ ] `CHANGELOG.md` exists with `[Unreleased]` section.
- [ ] Last release date matches the last git tag.

### 15. ADRs for big decisions
- [ ] `docs/adr/` exists.
- [ ] At least one ADR + `template.md`.

## Advanced checks

- [ ] **Health checks**: `/livez` and `/readyz` endpoints exist.
- [ ] **Error tracking**: Sentry or equivalent initialized.
- [ ] **Tracing**: OpenTelemetry instrumented (if microservice).
- [ ] **Resilience**: outbound HTTP calls have explicit timeouts.
- [ ] **Migrations**: `alembic/` exists if using a DB.
- [ ] **SECURITY.md**: present with reporting contact.
- [ ] **Pinned actions**: `.github/workflows/` uses SHA pins (advanced).
- [ ] **License**: `LICENSE` file matches `pyproject.toml` license field.

## Output format

Produce a Markdown report:

```markdown
# Repo Health Audit — <repo-name>

**Date:** YYYY-MM-DD
**Score:** X / 15 baseline + Y / 8 advanced

## ✅ Passing (N)
- ...

## ❌ Failing (N) — sorted by priority

### P0 (security / reproducibility)
1. **<check name>** — <evidence> → fix: <command or change>

### P1 (quality / CI)
...

### P2 (docs / governance)
...

## Recommended next steps
1. <highest-leverage fix>
2. ...
```

## Priority guidance

- **P0**: anything in checks 1, 2, 5, 9, 11 (reproducibility, secrets, container security).
- **P1**: checks 3, 4, 6, 7, 8, 10, 12 (quality + CI).
- **P2**: checks 13, 14, 15 + advanced (docs + governance).

## Fix loop

After presenting the report, **ask the user which items to fix**. For each agreed fix:
1. Reference the relevant section of the engineering standards for the fix.
2. Invoke the appropriate scaffold skill if it applies (e.g. missing CI → `scaffold-ci-cd`).
3. Otherwise make targeted edits and commit with the right Conventional Commit prefix.

## Forbidden

- Modifying files during the audit phase — audits are read-only.
- Skipping checks that "probably pass" — verify every one.
- Declaring PASS without running the verification command.
