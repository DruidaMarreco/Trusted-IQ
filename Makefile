.PHONY: setup install sync lock lint format type-check test integration audit all run evaluate

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
	python -m uv run ruff check src

format:
	python -m uv run black src

type-check:
	python -m uv run ty check src

test:  ## Unit tests + coverage (src/tests/unit_testing)
	python -m uv run pytest --cov --cov-report=term-missing

integration:  ## Run the integration examples against the API endpoints
	python -m uv run python src/integration_testing/test.py

audit:
	@python -m uv export --frozen --no-dev > .audit-reqs.txt && \
		python -m uv run pip-audit -r .audit-reqs.txt; \
		rm -f .audit-reqs.txt

run:  ## Start FastAPI dev server
	python -m uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

evaluate:  ## Run TradeIQ model evaluation (intent accuracy + groundedness; HTML report)
	python -m uv run python src/metrics_testing/evaluate_models.py --output results/model_eval.md

all: lint type-check test
