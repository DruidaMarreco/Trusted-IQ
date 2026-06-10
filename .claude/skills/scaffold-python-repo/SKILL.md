---
name: scaffold-python-repo
description: Use this skill when the user asks to bootstrap, scaffold, or initialize a new Python repository, or mentions setting up a new project with uv, ruff, mypy, and pre-commit. Covers Phases 1-2 of the engineering Quickstart (foundation + quality tooling).
---

# Scaffold Python Repo (Fases 1-2)

Bootstraps a new Python project with professional-grade foundation (uv, src-layout, deps split) and quality tooling (ruff, mypy, pre-commit, commit-msg hook, Makefile).

## When to use

- "Novo projecto Python"
- "Scaffold a repo"
- "Bootstrap project with uv"
- "Configura ruff e mypy"

## Pre-flight (ask the user)

1. **Project name** (kebab-case).
2. **Python version** (default `3.12`).
3. **Project type**: `lib` (default) or `app` (FastAPI/CLI).
4. **License** (default `MIT`).
5. **Confirm `uv` is installed** (`uv --version`); if not, run the installer.

## Steps

### 1. Initialise

```bash
uv init --lib <project-name>     # or --app
cd <project-name>
uv python pin <version>
uv python install
```

### 2. Create foundational files

- `.python-version` — already created by `uv python pin`.
- `.env.example` — empty template, **never** commit `.env`.
- `.dockerignore` — if app type.

**`.gitignore`** (full Python):

```gitignore
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
.env
.env.*
!.env.example
.idea/
.vscode/
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
.coverage
coverage.xml
*.log
logs/
data/
*.sqlite3
.DS_Store
```

**`.editorconfig`**:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

### 3. Populate `pyproject.toml`

```toml
[project]
name = "<project-name>"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # production deps — installed everywhere
]

[dependency-groups]
dev = [
    "ruff",
    "mypy",
    "pre-commit",
    "pytest",
    "pytest-cov",
    "pytest-mock",
    "pytest-asyncio",
    "pip-audit",
    "bandit",
    "deptry",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests that require external services",
    "slow: marks tests that take a long time to run",
]
addopts = "--strict-markers -v"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

**Rule:** if the app does `import X`, `X` goes in `[project] dependencies`. If it's a shell tool (`ruff check .`, `pytest`), it goes in `[dependency-groups] dev`.

### 4. Install dependencies

```bash
uv lock                     # generate uv.lock (MUST be committed)
uv sync --group dev
```

### 5. Pre-commit + commit-msg hook

**`.pre-commit-config.yaml`**:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.12
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.10

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
```

If mypy reports missing stubs for a lib (e.g. `types-requests`), add them to `additional_dependencies`.

**`.githooks/commit-msg`** (Conventional Commits enforcer):

```bash
#!/usr/bin/env bash
MSG_FILE="$1"
MSG=$(cat "$MSG_FILE")

if echo "$MSG" | grep -qE "^(Merge|Revert) "; then exit 0; fi

PATTERN="^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?(!)?: .{1,}"

if ! echo "$MSG" | grep -qE "$PATTERN"; then
  echo ""
  echo "❌ Commit message não segue Conventional Commits."
  echo "   Formato: <tipo>(âmbito opcional): <descrição>"
  echo "   Tipos: feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert"
  echo "   Recebido: $MSG"
  exit 1
fi
exit 0
```

```bash
chmod +x .githooks/commit-msg
```

### 6. Makefile

```makefile
.PHONY: setup install sync lock lint format type-check test test-integration audit all

setup:                               ## First install + git hooks
	uv sync --group dev
	uv run pre-commit install
	cp .githooks/commit-msg .git/hooks/commit-msg
	chmod +x .git/hooks/commit-msg

install: setup

sync:                                ## Sync deps from lockfile
	uv sync --group dev

lock:                                ## Regenerate uv.lock
	uv lock

lint:
	uv run ruff check .

format:
	uv run ruff format .

type-check:
	uv run mypy .

test:
	uv run pytest tests/unit --cov --cov-report=term-missing

test-integration:
	uv run pytest tests/integration -m integration

audit:
	@uv export --frozen --no-dev > .audit-reqs.txt && \
		uv run pip-audit -r .audit-reqs.txt; \
		rm -f .audit-reqs.txt

all: lint type-check test
```

### 7. Source layout

```
src/<package_name>/__init__.py   (created by uv init)
```

### 8. First commits (Conventional Commits)

```bash
git init
git add .
git commit -m "chore: scaffold project structure"
uv run pre-commit install
make setup                       # installs commit-msg hook
git add .pre-commit-config.yaml .githooks/ Makefile
git commit -m "chore: add tooling (ruff, mypy, pre-commit, commit-msg hook)"
```

## Validation

Before finishing, run:
```bash
uv run pre-commit run --all-files
uv run ruff check .
uv run mypy .
```

All must pass. If `mypy` complains about missing stubs, add them to `additional_dependencies` in `.pre-commit-config.yaml`.

## Hand-off

Recommend the user invoke `scaffold-tests` next.
