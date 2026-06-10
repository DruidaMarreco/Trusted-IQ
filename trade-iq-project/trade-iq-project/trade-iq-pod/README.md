# trade-iq-pod

LangChain orchestrator agent with subagents and FastAPI exposure.

## What it does

`trade-iq-pod` is a provider-agnostic LLM orchestration layer built on LangChain and FastAPI. An orchestrator agent decomposes user queries, delegates work to specialised subagents (A and B), calls tools, and returns a synthesised answer. The LLM provider (Azure OpenAI, OpenAI, Anthropic, Ollama) is configurable at runtime via environment variables, with per-agent model overrides.

## Quickstart

```bash
git clone <repo>
cd trade-iq-pod
make setup        # installs deps + pre-commit hooks
make test         # runs unit test suite
make run          # starts FastAPI dev server on :8000
```

Health endpoints available after startup:
- `GET /livez` — liveness probe
- `GET /readyz` — readiness probe (returns version)

## Configuration

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `azure_openai` | `azure_openai` \| `openai` \| `anthropic` \| `ollama` |
| `LLM_MODEL` | `gpt-4o` | Base model for all agents |
| `ENV` | `dev` | `dev` \| `staging` \| `prod` |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
make lint          # ruff check
make format        # black
make type-check    # ty
make test          # unit tests + coverage
make audit         # pip-audit dependency scan
make evaluate      # TradeIQ model evaluation
```

### Model evaluation

`make evaluate` runs the **GenAI Sales Assistant flow** (Intent Classifier →
mock TextToSQL/Optimizer tool → grounded Response Generator) for each candidate
model and scores them on **intent accuracy, groundedness, relevance and
format**, writing `results/model_eval.md` to pick the best model(s).
Groundedness is judged both by an LLM rubric and a deterministic figure-overlap
check (the answer's numbers must appear in the tool output — no fabrication).

By default it runs `--backend claude_code`: the Claude family (Opus / Sonnet /
Haiku) is called **through Claude Code, billed to your subscription quota**.

- **Local:** be logged in to the `claude` CLI — auth is automatic.
- **CI / headless:** set `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`)
  and leave `ANTHROPIC_API_KEY` unset (it would override the subscription).
- To evaluate the metered multi-provider set instead:
  `uv run python scripts/evaluate_models.py --backend providers`.

## Documentation

- [Contributing](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/)
- [Changelog](CHANGELOG.md)
- [Security](SECURITY.md)

## License

Proprietary — All rights reserved. See [LICENSE](LICENSE).
