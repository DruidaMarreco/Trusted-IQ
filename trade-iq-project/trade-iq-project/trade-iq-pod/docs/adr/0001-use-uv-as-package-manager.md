# ADR-0001: Use uv as Python package manager

- **Status:** Accepted
- **Date:** 2026-05-01
- **Deciders:** [@diogrocha]

## Context

Need a fast, deterministic Python package manager with lockfile support, virtual env management, and good DX. Traditional options (pip + venv, poetry, pipenv) have varying levels of lock reliability and speed.

## Decision

Use [uv](https://docs.astral.sh/uv/) as the single tool for venv creation, dependency installation, lockfile management, and script running.

## Alternatives Considered

- **pip + pip-tools** — fast but separate tools, no unified CLI
- **Poetry** — mature ecosystem but slow resolver, non-standard `pyproject.toml` extensions
- **Pipenv** — lockfile support but slow and largely unmaintained

## Consequences

### Positive
- Single CLI for all package operations (`uv add`, `uv sync`, `uv run`, `uv lock`)
- Fastest resolver available (Rust-based)
- `uv.lock` is fully reproducible across platforms
- Native `pyproject.toml` standards compliance

### Negative / Trade-offs
- Relatively new tool — smaller community vs pip/poetry
- Team must install `uv` before `make setup` (documented in README)
