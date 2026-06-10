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
make benchmark     # LLM benchmark (set RUNS=N)
```

## Documentation

- [Contributing](CONTRIBUTING.md)
- [Architecture decisions](docs/adr/)
- [Changelog](CHANGELOG.md)
- [Security](SECURITY.md)

## License

Proprietary — All rights reserved. See [LICENSE](LICENSE).
