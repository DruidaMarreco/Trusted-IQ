# ADR-0003: Keep a deterministic thin orchestrator as production; test agentic tool use alongside

- **Status:** Accepted
- **Date:** 2026-06-11
- **Deciders:** [@simao-miguel]

## Context

The assistant must route a user query to the right backend tool (CDT TextToSQL
or ERDC Optimizer) and return a grounded answer. There are two ways to decide
*which tool to use*:

1. **Deterministic** — the LLM classifies the intent, and code maps the intent
   to a tool (the thin-orchestrator pattern, [ADR-0002](0002-langchain-provider-agnostic-factory.md)).
2. **Model-driven (agentic)** — give the LLM the tools and let it decide whether
   and which to call, via native tool-calling.

We need the assistant to be reliable, provider-agnostic and evaluable today, but
we also want to validate that the model can *itself* understand it needs a tool
— the basis for future agentic features.

## Decision

Ship **both**, with distinct roles:

- The **thin orchestrator** (`OrchestratorAgent`) is the **production** path
  behind `POST /agent/invoke`: classify intent → deterministic `route_to_tool` →
  grounded response. No native tool-calling.
- The **agentic orchestrator** (`AgenticOrchestrator`) is a **capability test
  and future-feature seed**: Claude is given the CDT/ERDC tools and decides for
  itself, via the Claude Agent SDK's native tool-use loop on the subscription
  quota. It reports the tools it actually invoked so we can measure
  tool-selection accuracy.

## Alternatives Considered

- **Agentic only (native tool-calling everywhere)** — discarded for the
  production path: native tool-calling APIs differ across providers, which would
  break the provider-uniform model evaluation and add per-provider glue; it is
  also less deterministic and harder to unit-test.
- **Thin only** — sufficient for production, but leaves the question "can the
  agent decide to use a tool?" untested, and gives us nothing to build richer
  agentic behaviour on.
- **LangChain `bind_tools` for the agentic path** — viable for metered API
  providers, but requires API keys; the Claude Agent SDK gives native tool use
  on the **subscription quota** with no key, matching our current constraints.

## Consequences

### Positive

- Production stays deterministic, provider-agnostic and fully testable.
- We can measure two complementary things: **intent-classification accuracy**
  (thin) and **tool-selection accuracy** (agentic) — the latter scored 6/6 on
  Sonnet (see [orchestration.md](../orchestration.md)).
- Both share the same [tool layer](../tools.md) (live-or-mock) and grounding
  prompt, so behaviour is consistent.
- A clear path to richer agentic features (multi-step, tool chaining) without
  disturbing the production path.

### Negative / Trade-offs

- Two orchestrators to maintain.
- The agentic path currently requires the Claude Agent SDK backend (not
  provider-uniform), and incurs extra turns/latency from the SDK's `ToolSearch`
  tool-discovery step.
- Agentic tool selection is prompt-sensitive (an over-cautious prompt scored
  4/6 before tuning) — it needs evaluation guardrails before any production use.
