.PHONY: setup install sync lock lint format type-check test test-integration audit all run benchmark

setup:  ## First install + git hooks
	python -m uv sync --group dev
	python -m uv run pre-commit install
	cp .githooks/commit-msg .git/hooks/commit-msg
	chmod +x .git/hooks/commit-msg

install: setup

sync:  ## Sync deps from lockfile
	python -m uv sync --group dev

lock:  ## Regenerate uv.lock
	python -m uv lock

lint:
	python -m uv run ruff check .

format:
	python -m uv run ruff format .

type-check:
	python -m uv run mypy .

test:
	python -m uv run pytest tests/unit --cov --cov-report=term-missing

test-integration:
	python -m uv run pytest tests/integration -m integration

audit:
	@python -m uv export --frozen --no-dev > .audit-reqs.txt && \
		python -m uv run pip-audit -r .audit-reqs.txt; \
		rm -f .audit-reqs.txt

run:  ## Start FastAPI dev server
	python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

benchmark:  ## Run LLM benchmark (RUNS=3 by default)
	python -m uv run python scripts/benchmark_models.py --runs $(or $(RUNS),3) --output results/benchmark.md

all: lint type-check test
