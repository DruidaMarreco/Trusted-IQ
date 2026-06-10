# TradeIQ TPO — GenAI Sales Assistant

The GenAI **Sales Assistant** for the TradeIQ **Trade Promotion Optimisation (TPO)**
platform — a provider-agnostic LLM service (LangChain + FastAPI) that answers CPG
commercial-planning questions in plain language, grounded in the platform's data
and optimizer.

It is the conversational layer over a proven ML optimisation engine: Key Account
Managers, Trade Marketing Managers and Commercial Directors ask *why* a promotion
was recommended or *what* the best options are for a remaining budget, and the
assistant routes the question to the right tool and returns a grounded answer.

---

## Architecture — a thin orchestrator

A single LLM classifies the user's **intent** and routes to one tool, then a
second prompt turns the tool's output into a business answer. There is **no
multi-agent system and no RAG** — answers are grounded in structured tool output
(see [ADR-0002](docs/adr/) and [docs/architecture.md](docs/architecture.md)).

```
            ┌─────────────────────┐
user query →│  Intent Classifier  │  (PROMPT-001)
            └─────────┬───────────┘
                      │  intent + extracted params
        ┌─────────────┼──────────────┬───────────────┐
        ▼             ▼              ▼               ▼
   DATA_QUERY    OPTIMIZER_RUN   CLARIFICATION   OUT_OF_SCOPE
        │             │              │               │
  TextToSQL agent  Optimizer API   ask follow-up   decline
        └─────────────┴──────────────┘
                      │  tool_output (rows / ranked options)
            ┌─────────▼───────────┐
            │ Response Generator  │  (PROMPT-002) → grounded NL answer
            └─────────────────────┘
```

- **Intents:** `DATA_QUERY` · `OPTIMIZER_RUN` · `CLARIFICATION` · `OUT_OF_SCOPE`
- **Grounding:** the response must use only the `tool_output` — never fabricate
  numbers. This is what the model evaluation measures.
- Canonical prompts live in [src/app/prompts.py](src/app/prompts.py).

## Repository layout

```
.                       config + metadata at the root
├── pyproject.toml  Makefile  uv.lock  .pre-commit-config.yaml  .python-version
├── .github/workflows/  ci.yml · metrics.yml (disabled) · cd.yml (disabled)
├── docs/               architecture, testing, model-evaluation, ADRs, diagrams
└── src/                all code and tests
    ├── app/                  the service (FastAPI + orchestrator + tools)
    ├── tests/
    │   ├── unit_testing/     fast, mocked unit tests (no network)
    │   └── data/             ground-truth datasets (intent_dataset.json)
    ├── integration_testing/  test.py — example calls against the API endpoints
    └── metrics_testing/      evaluate_models.py — mass model eval + HTML report
```

## Quickstart

This project uses [`uv`](https://docs.astral.sh/uv/) for everything.

```bash
make setup        # uv sync + pre-commit hooks
make run          # FastAPI dev server on :8000
make test         # unit tests + coverage
```

Health endpoints: `GET /livez` (liveness), `GET /readyz` (readiness + version).
Assistant endpoint: `POST /agent/invoke` with `{"query": "...", "session_id": "..."}`.

## Testing tiers

| Tier | Location | What it is | Run |
|------|----------|-----------|-----|
| Unit | `src/tests/unit_testing/` | Fast, mocked, deterministic | `make test` |
| Integration | `src/integration_testing/test.py` | Example calls to each endpoint | `make integration` |
| Metrics | `src/metrics_testing/` | Mass model evaluation → HTML report | `make evaluate` |

See [docs/testing.md](docs/testing.md) for details.

## Model evaluation (choose the best model)

`make evaluate` runs the full assistant flow for each candidate model and scores
them on **intent accuracy, groundedness, relevance and format**, writing
`results/model_eval.md` and `results/model_eval.html`. Groundedness is judged by
both an LLM rubric and a deterministic figure-overlap check (every number in the
answer must appear in the tool output). By default it runs `--backend
claude_code`, billing the **Claude Code subscription quota** (Opus/Sonnet/Haiku).

- **Local:** be logged in to the `claude` CLI — auth is automatic.
- **CI / headless:** set `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`); keep
  `ANTHROPIC_API_KEY` unset or it overrides the subscription.
- Metered providers instead: `uv run python src/metrics_testing/evaluate_models.py --backend providers`.

Full details: [docs/model-evaluation.md](docs/model-evaluation.md).

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `azure_openai` | `azure_openai` \| `openai` \| `anthropic` \| `claude_code` \| `ollama` |
| `LLM_MODEL` | `gpt-4o` | Base model for all agents |
| `LLM_PROXY_BASE_URL` | _(empty)_ | If set, route all models through one OpenAI-compatible gateway |
| `ENV` / `LOG_LEVEL` | `dev` / `INFO` | Runtime + logging |

## Development

```bash
make lint          # ruff check src
make format        # black src
make type-check    # ty check src
make audit         # pip-audit dependency scan
```

Toolchain: **black** (format) · **ruff** (lint) · **ty** (types) · **pytest** —
all pinned in `uv.lock` and enforced in CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Documentation

- [Architecture](docs/architecture.md) — the thin-orchestrator design
- [Testing](docs/testing.md) — the three testing tiers
- [Model evaluation](docs/model-evaluation.md) — how models are scored & chosen
- [Architecture decisions](docs/adr/) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## License

Proprietary — All rights reserved. See [LICENSE](LICENSE).
