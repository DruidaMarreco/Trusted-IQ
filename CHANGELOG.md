# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Thin orchestrator** (`OrchestratorAgent`): classify intent (PROMPT-001) → route → grounded response (PROMPT-002), with four intents (`DATA_QUERY`, `OPTIMIZER_RUN`, `CLARIFICATION`, `OUT_OF_SCOPE`)
- **Agentic orchestrator** (`AgenticOrchestrator`): model-driven native tool use via the Claude Agent SDK on the subscription quota; tool-selection test scoring 6/6 on Sonnet
- **Tool integration layer** (`app/tools/`): CDT TextToSQL + ERDC Optimizer over HTTP with **mock fallback**, retries, `Bearer` auth, `ToolError`, and runnable contract stubs (`tool_stubs.py`)
- **Claude Code backend** (`ChatClaudeCode`) using the Claude Agent SDK — runs on the subscription quota (no metered API key)
- **Model evaluation** (`evaluate_models.py`): intent accuracy + groundedness (LLM judge + figure-overlap) + relevance + format → composite & value index; per-round HTML/XLSX/JSON artifacts, confusion matrix, and cross-round trend; Opus pinned as the orchestrator model
- Per-call/per-turn usage **metrics** (latency, tokens, estimated cost) surfaced on `/agent/invoke`
- `/agent/invoke` accepts `account_scope`, `planning_period` and `history` context
- Structured logging with `structlog`; correlation IDs via `X-Request-ID`; `/livez` + `/readyz` probes
- `SecretStr` wrapping for all API-key/secret fields
- Dockerfile (AKS / Container Apps) and documentation set under `docs/` (architecture, orchestration, tools, testing, model-evaluation, model-landscape, ADR-0003)

### Changed
- Replaced the subagent-A/B delegation design with the single thin orchestrator (grounding from structured tool output — **no multi-agent, no RAG**; see ADR-0002)
- Standardised the toolchain on **black + ruff + ty + pytest** (dropped mypy); enforced in CI
- Pinned `LLM_MODEL=claude-opus-4-8` (chosen by the model evaluation)

### Removed
- `tpo_tools.py` single mock module (superseded by the `app/tools/` package)

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
