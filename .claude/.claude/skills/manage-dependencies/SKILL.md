---
name: manage-dependencies
description: Use this skill when the user asks to add, remove, upgrade, or audit Python dependencies in a uv-managed project. Enforces the prod/dev split, lockfile sync, and security audit workflow.
---

# Manage Dependencies

Day-to-day dependency management for uv-managed Python projects.

## When to use

- "Adiciona <lib>"
- "Remove <lib>"
- "Upgrade dependencies"
- "Audita deps"
- "pip-audit"

## Pre-flight

- Confirm `uv` is the package manager (look for `uv.lock`). If not, refuse and explain.
- Confirm the working tree is clean (`git status`). Refuse to add deps on top of unrelated changes.

## Decision tree

### Add a dependency

**Question to ask first:** does the application code `import` it?
- **Yes (`import X` in `src/`)** → production dep → `uv add <lib>`.
- **No (only used in shell, tests, or tooling)** → dev dep → `uv add --group dev <lib>`.

**Common mis-classifications:**
- `httpx` is **production** (the app imports it).
- `pytest`, `ruff`, `mypy`, `bandit`, `pip-audit` are **dev**.
- `pytest-asyncio`, `respx` are **dev**.
- `pydantic-settings`, `structlog`, `sentry-sdk` are **production**.

### Remove a dependency

```bash
uv remove <lib>                # or uv remove --group dev <lib>
```

Then **search the codebase** for `import <lib>` to confirm nothing breaks:
```bash
grep -rn "import <lib>\|from <lib>" src/ tests/
```

### Upgrade a dependency

```bash
uv lock --upgrade-package <lib>            # single package
uv lock --upgrade                          # everything
```

After upgrade, **always**:
1. Run full test suite: `make all`.
2. Check the changelog of the upgraded lib for breaking changes.
3. Run `uv run pip-audit` to confirm no new CVEs introduced.

### Audit dependencies

```bash
make audit                       # pip-audit
uv run deptry .                  # unused / missing deps
uv tree                          # dependency tree
```

If `pip-audit` reports CVEs:
1. Check if a fix version exists: `uv lock --upgrade-package <vulnerable-lib>`.
2. If no fix yet: document in `CHANGELOG.md` under `[Unreleased] / Security` and consider pinning to a workaround or filing an issue upstream.
3. Re-run `pip-audit` to confirm.

## Mandatory checks after any change

```bash
uv sync --group dev --frozen     # confirms lockfile is in sync
make lint                        # ruff
make type-check                  # mypy
make test                        # pytest
make audit                       # pip-audit
```

If `--frozen` fails, the lockfile is out of sync: run `uv lock` and commit.

## Commit format

Conventional Commits:

- Adding: `chore(deps): add httpx`
- Removing: `chore(deps): remove unused requests`
- Upgrading dev: `chore(deps-dev): upgrade ruff to v0.11.12`
- Upgrading prod: `chore(deps): upgrade httpx to v0.28 (CVE-2024-XXXX)`
- Security fix: `fix(deps): upgrade cryptography to patch CVE-2026-XXXX` (use `fix:` not `chore:` for CVE fixes — they go in CHANGELOG)

## Files to commit together

`pyproject.toml` **AND** `uv.lock` — never one without the other. If only `pyproject.toml` changes, the build is non-reproducible.

## Forbidden

- `pip install <lib>` inside a uv project — bypasses the lockfile.
- Committing only `pyproject.toml` without re-locking.
- Adding deps to satisfy a one-off script; use `uvx <tool>` for ephemeral tools.
- Pinning to exact versions (`==`) without justification — let the resolver pick the range; the lockfile pins the exact resolved version.

## CHANGELOG impact

| Change | CHANGELOG entry? |
|---|---|
| Add/remove a dev dep | ❌ no |
| Add a production dep (user-visible feature) | ✅ `Added` |
| Upgrade with CVE fix | ✅ `Security` |
| Upgrade with breaking change to API consumers | ✅ `Changed` (or `Removed`) |
| Routine dependabot bump | ❌ no |
