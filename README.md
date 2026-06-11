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

### Orchestrators

The service ships three orchestrators that differ in **who decides which tool to
use** — see [docs/orchestration.md](docs/orchestration.md):

- **Thin orchestrator** (`OrchestratorAgent`, **production**) — deterministic:
  the LLM classifies intent, then code routes to the tool. Provider-agnostic,
  fully testable; measures **intent-classification accuracy**.
- **Agentic orchestrator** (`AgenticOrchestrator`) — model-driven via the Claude
  Agent SDK (subscription quota): Claude *decides* whether/which tool to call.
  Tool-selection: 6/6 on Sonnet.
- **Native tool-calling** (`ToolCallingOrchestrator`) — provider-agnostic
  model-driven tool use via LangChain `bind_tools`; the agentic path for the
  **Azure**-based deployment. Tool-selection: 4/4 on Azure `gpt-4o`.

Tools (CDT TextToSQL, ERDC Optimizer) call their **live** service over HTTP when
configured, and fall back to deterministic **mock** output otherwise — see
[docs/tools.md](docs/tools.md).

## Repository layout

```
.                       config + metadata at the root
├── pyproject.toml  Makefile  uv.lock  .pre-commit-config.yaml  .python-version
├── .github/workflows/  ci.yml · metrics.yml (disabled) · cd.yml (disabled)
├── docs/               architecture, testing, model-evaluation, ADRs, diagrams
└── src/                all code and tests
    ├── app/                  the service
    │   ├── agents/           orchestrator.py (thin) · agentic_orchestrator.py (Claude SDK) · tool_calling_orchestrator.py (bind_tools)
    │   ├── tools/            CDT/ERDC integrations — registry · cdt · erdc · http · mock
    │   ├── api/routes.py     /agent/invoke
    │   ├── prompts.py · llm_factory.py · claude_code_llm.py · metrics.py · eval.py · config.py
    │   └── schemas/models.py
    ├── tests/
    │   ├── unit_testing/     fast, mocked unit tests (no network)
    │   └── data/             ground-truth datasets (intent_dataset.json)
    ├── integration_testing/  test.py (endpoints) · agentic_tool_test.py · tool_stubs.py
    └── metrics_testing/      evaluate_models.py — mass model eval + artifacts
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
them on **intent accuracy, groundedness, relevance and format**, writing a
timestamped + `_latest` artifact set per round — **`.md`, `.html`** (chart +
confusion matrix + per-question tables), **`.xlsx`** (5 sheets) and **`.json`** —
plus a cross-round `history.csv`. Groundedness is judged by both an LLM rubric
and a deterministic figure-overlap check (every number in the answer must appear
in the tool output). By default it runs `--backend claude_code`, billing the
**Claude Code subscription quota** (Opus/Sonnet/Haiku). Current pick: **Opus**
(top composite), **Haiku** the cost fallback — see
[docs/model-evaluation.md](docs/model-evaluation.md#results).

- **Local:** be logged in to the `claude` CLI — auth is automatic.
- **CI / headless:** set `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`); keep
  `ANTHROPIC_API_KEY` unset or it overrides the subscription.
- Metered providers instead: `uv run python src/metrics_testing/evaluate_models.py --backend providers`.

Full details: [docs/model-evaluation.md](docs/model-evaluation.md).

## Configuration

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `azure_openai` | `azure` (Azure AI Foundry, OpenAI-compatible) \| `azure_openai` \| `openai` \| `anthropic` \| `claude_code` \| `ollama` |
| `LLM_MODEL` | `claude-opus-4-8` | Orchestrator model / Foundry **deployment name** (e.g. `gpt-4o`) — any deployed model works by name |
| `LLM_PROXY_BASE_URL` | _(empty)_ | If set, route all models through one OpenAI-compatible gateway |
| `CDT_BASE_URL` / `ERDC_BASE_URL` | _(empty)_ | Tool service URLs; **empty = deterministic mock**, set = live HTTP (see [docs/tools.md](docs/tools.md)) |
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

- [Architecture](docs/architecture.md) — end-to-end design, both orchestrators, code map
- [Orchestration](docs/orchestration.md) — thin (deterministic) vs agentic (model-driven) + tool-selection results
- [Tools](docs/tools.md) — CDT/ERDC integrations: live HTTP + mock fallback, contracts, stubs
- [Testing](docs/testing.md) — the three testing tiers
- [Model evaluation](docs/model-evaluation.md) — how models are scored & chosen, with results
- [Model landscape](docs/model-landscape.md) — candidate families (GPT / Claude / Gemini)
- [Architecture decisions](docs/adr/) — ADR-0001 (uv) · ADR-0002 (provider-agnostic factory) · ADR-0003 (agentic vs thin)
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## License

Proprietary — All rights reserved. See [LICENSE](LICENSE).
