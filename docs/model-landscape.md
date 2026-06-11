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
- **Provider-agnostic by design:** swapping families is an `.env` change
  (`LLM_PROVIDER` / `LLM_MODEL`) — see [ADR-0002](adr/0002-langchain-provider-agnostic-factory.md).

## Test matrix (prepared for future runs)

The candidate set for upcoming comparisons (`MODEL_MATRIX` in
`evaluate_models.py`). Each model routes to its own backend; `--backend matrix`
runs whatever is reachable and **auto-skips the rest**.

| Vendor | Cheap | Medium | Strong | Backend | Ready? |
|--------|-------|--------|--------|---------|--------|
| **OpenAI** | `gpt-5.4-mini` | `gpt-5.4` | `gpt-5.5` | `azure` (Foundry deployment) | ⏳ must be **deployed** in Foundry (only `gpt-4o` is today) |
| **Anthropic** | `claude-haiku-4-5` | `claude-sonnet-4-6` | `claude-opus-4-8` | `claude_code` (subscription) | ✅ **ready now** (aliases `haiku`/`sonnet`/`opus`) |
| **Google** | `gemini-2.5-flash-lite` | `gemini-2.5-flash` | `gemini-2.5-pro` | `google` (Gemini API) | ⏳ needs `GOOGLE_API_KEY` (not in Azure Foundry) |

To run the full matrix once everything is available:

```bash
uv run python src/metrics_testing/evaluate_models.py --backend matrix
```

To light up the pending tiers:
- **OpenAI:** deploy `gpt-5.4-mini` / `gpt-5.4` / `gpt-5.5` in the Foundry portal
  (the deployment name must match, or edit `AZURE_MODELS` / `MODEL_MATRIX`).
- **Google:** set `GOOGLE_API_KEY` in `.env`.
- **Anthropic:** already works via the Claude Code subscription quota.

Prices for cost estimation are in `app/metrics.py` (approximate for the new
models; refine when published).
