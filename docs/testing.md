# Testing strategy

Three distinct tiers, each in its own directory under `src/`.

## 1. Unit testing — `src/tests/unit_testing/`

Fast, deterministic, **no network**. All LLM and tool calls are mocked. This is
what CI gates on and what `make test` runs.

```bash
make test          # pytest + coverage (config in pyproject [tool.pytest])
```

- `pythonpath = ["src"]` and `testpaths = ["src/tests/unit_testing"]` are set in
  `pyproject.toml`, so `import app...` resolves with no manual `PYTHONPATH`.
- Coverage is reported (`--cov`); the 80% gate is configured for local runs and
  relaxed in CI (`--cov-fail-under=0`) until the suite grows.
- Ground-truth data shared with the metrics tier lives in `src/tests/data/`.

Current coverage: the pure helpers (`eval.py`), tools (`tpo_tools.py`), the LLM
factory routing, the orchestrator and the sample tool.

## 2. Integration testing — `src/integration_testing/test.py`

The "singular tests" tier: a hands-on, runnable walkthrough of **every HTTP
endpoint** with example requests/responses, using FastAPI's `TestClient`.

```bash
make integration   # uv run python src/integration_testing/test.py
```

- Exercises `/livez`, `/readyz` (no LLM) and `/agent/invoke` (calls the
  configured LLM backend — defaults to Claude Code).
- Intended for manual/demo verification, not as a CI gate. The `/agent/invoke`
  example needs a working LLM backend / auth; it fails gracefully otherwise.

## 3. Metrics testing — `src/metrics_testing/`

Mass model-quality evaluation that runs the full assistant flow for each
candidate model and produces a comparison report (markdown **and HTML**).

```bash
make evaluate      # → results/model_eval.md + results/model_eval.html
```

Scores each model on intent accuracy, groundedness, relevance and format. See
[model-evaluation.md](model-evaluation.md). Wired into the disabled
`metrics.yml` workflow for scheduled/manual cloud runs.

## What runs where

| | Unit | Integration | Metrics |
|---|---|---|---|
| Network / LLM | mocked | real (optional) | real (mass) |
| In CI by default | ✅ (ci.yml) | ✗ | ✗ (metrics.yml, disabled) |
| Cost | none | low | quota / API spend |
| Purpose | correctness | endpoint sanity | model selection |
