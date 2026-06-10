# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Structured logging with `structlog` (console in dev, JSON in prod)
- Correlation IDs via `X-Request-ID` middleware
- `/livez` and `/readyz` health endpoints
- `env` and `log_level` runtime settings in `config.py`
- `SecretStr` wrapping for all API key fields

### Changed
- Orchestrator migrated to LangChain 0.3+ `create_agent` API (removed deprecated `AgentExecutor`)

## [0.1.0] — 2026-05-01

### Added
- Initial project scaffolding with LangChain orchestrator + FastAPI
- Provider-agnostic LLM factory (`azure_openai` | `openai` | `anthropic` | `ollama`)
- Per-agent model overrides via environment variables
- Orchestrator agent with subagent A and B delegation
- Sample tool integration
- `pydantic-settings` config validation at boot
- `pre-commit` hooks: ruff, mypy, detect-private-key
- Conventional Commits enforcement via `.githooks/commit-msg`
- LLM benchmark script for orchestrator model selection
- Intent routing benchmark dimension
