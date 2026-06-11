# Model landscape — candidate families

Context for which models are worth evaluating as the orchestrator LLM. The
TradeIQ orchestrator needs strong **reasoning + explanation** (justify a
recommendation) and reliable **structured output** (intent JSON, grounded
figures). The empirical comparison and the pinned choice live in
[model-evaluation.md](model-evaluation.md); this page is the qualitative map.

## Families

### OpenAI (GPT)
- **GPT-5.x** — strongest for agents / reasoning.
- **GPT-4o** — good quality/cost balance.
- **GPT-4o mini** — ultra-cheap; suited to judge/secondary roles.

### Anthropic (Claude)
- **Opus** — very strong reasoning + explanation; ideal for the "explain why a
  promotion was recommended" workload. **Pinned production model.**
- **Sonnet** — excellent cost/quality; common production default; strong at
  tool use (6/6 on the agentic tool-selection test).
- **Haiku** — cheapest; best quality-per-dollar in our eval; the cost-sensitive
  fallback and the evaluation judge.

### Google (Gemini)
- **Gemini Pro / 3.x** — strong at data integration and structured reasoning;
  in our experience less consistent than OpenAI/Claude on agentic tool use.

## How this maps to the codebase

- **Pinned now:** `LLM_MODEL=claude-opus-4-8` (top composite), Haiku fallback —
  see [model-evaluation.md](model-evaluation.md#results).
- **Evaluated so far:** Claude only (subscription quota). GPT and Gemini require
  metered API keys via `--backend providers`; the harness is ready for them
  (extend `PROVIDER_MODELS`, add a `google_genai` branch to `build_llm`, and
  prices in `app/metrics.py`).
- **Provider-agnostic by design:** swapping families is an `.env` change
  (`LLM_PROVIDER` / `LLM_MODEL`) — see [ADR-0002](adr/0002-langchain-provider-agnostic-factory.md).
