# ADR-0002: Use LangChain with provider-agnostic LLM factory

- **Status:** Accepted
- **Date:** 2026-05-01
- **Deciders:** [@diogrocha]

## Context

The orchestrator needs to call LLMs from multiple providers (Azure OpenAI, OpenAI, Anthropic, Ollama). Hardcoding a single provider creates vendor lock-in and makes model benchmarking difficult.

## Decision

Use LangChain as the abstraction layer with a central `build_llm()` factory function that reads provider and model from `pydantic-settings`. Each agent receives its LLM at construction time (dependency injection).

## Alternatives Considered

- **Direct provider SDKs** — faster, no abstraction overhead, but requires rewrite to switch providers
- **LiteLLM** — wider provider support but less integrated with the LangChain agent/tool ecosystem
- **OpenAI-compatible endpoints only** — simpler but excludes Anthropic native API

## Consequences

### Positive
- Swap provider via env var, zero code change
- Per-agent model overrides (`ORCHESTRATOR_MODEL`, `SUBAGENT_A_MODEL`, etc.)
- LangChain tool ecosystem available out of the box

### Negative / Trade-offs
- LangChain API surface changes frequently (e.g. `AgentExecutor` removed in 0.3)
- Additional abstraction layer adds latency (~1-2ms) and bundle size
