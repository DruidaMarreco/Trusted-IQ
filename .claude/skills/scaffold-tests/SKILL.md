---
name: scaffold-tests
description: Use this skill when the user asks to set up the testing infrastructure for a Python project — pytest, coverage, fixtures, unit/integration split. Covers Phase 3 of the engineering Quickstart.
---

# Scaffold Tests (Fase 3)

Sets up `tests/`, fixtures, coverage, and the first smoke test.

## When to use

- "Configurar testes"
- "Setup pytest"
- "Add coverage"
- After `scaffold-python-repo`.

## Pre-conditions

- `pyproject.toml` already has `pytest`, `pytest-cov`, `pytest-mock`, `pytest-asyncio` in `[dependency-groups] dev`.
- `uv sync --group dev` has been run.

## Steps

### 1. Create the tests tree

```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   └── test_smoke.py
├── integration/
│   ├── __init__.py
│   └── (empty)
└── e2e/
    └── (created only if requested)
```

### 2. `tests/conftest.py`

Minimal shared fixtures. Example:

```python
import pytest

@pytest.fixture
def sample_data() -> dict:
    return {"id": 1, "name": "test"}
```

### 3. First smoke test

`tests/unit/test_smoke.py`:

```python
def test_import() -> None:
    import <package_name>
    assert <package_name> is not None
```

This proves the pipeline works end-to-end before any business logic exists.

### 4. Validate `pyproject.toml` test config

Must include:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests that require external services",
    "slow: marks tests that take a long time to run",
]
addopts = "--strict-markers -v"
asyncio_mode = "auto"           # only if pytest-asyncio is used

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

### 5. Confirm Makefile targets

Must have `test` and `test-integration`:

```makefile
test:
	uv run pytest tests/unit --cov --cov-report=term-missing

test-integration:
	uv run pytest tests/integration -m integration
```

### 6. Run

```bash
make test                       # unit only
make test-integration           # integration only (uses -m integration)
```

The smoke test must pass with coverage report.

### 7. Commit

```bash
git add tests/ pyproject.toml
git commit -m "test: scaffold pytest with smoke test and coverage"
```

## Rules to enforce

- **Never** add `if __name__ == "__main__"` runners.
- **Never** call real APIs in unit tests — use mocks/fixtures.
- Unit tests must run **offline** and **deterministically**.
- Integration tests marked with `@pytest.mark.integration`.

## Hand-off

Recommend the user invoke `scaffold-ci-cd` next.
