# Model evaluation — choosing the orchestrator model

[`src/metrics_testing/evaluate_models.py`](../src/metrics_testing/evaluate_models.py)
implements the **[ML] Orchestrator Agent Model Evaluation & Testing** task: it
runs the real TradeIQ assistant flow for each candidate model and scores them so
the best one(s) can be chosen.

```bash
make evaluate
# or
uv run python src/metrics_testing/evaluate_models.py --intent-sample 24 --backend claude_code
```

## What it measures

**1. Intent classification accuracy** — runs PROMPT-001 over the ground-truth
dataset ([`src/tests/data/intent_dataset.json`](../src/tests/data/intent_dataset.json),
60 labelled queries across the four intents) and compares predicted vs. label.
The dataset is grouped by intent, so a small `--intent-sample N` is **stride-sampled**
to span all four intents (e.g. N=12 → 4 DATA / 4 OPT / 2 CLARIFY / 2 OOS).

**2. Grounded response generation** — for grounded cases (query → deterministic
mock output via `app.tools`, so scores are reproducible), runs PROMPT-002 and
scores each answer:

| Dimension | How |
|---|---|
| **Groundedness** | LLM judge (1–5) **and** a deterministic figure-overlap check — every number in the answer must appear in the tool output (catches fabrication) |
| **Relevance** | LLM judge (1–5): does it answer the question? |
| **Format** | LLM judge (1–5): concise business language, bold figures, a next step |

A **composite** score (0–1) combines intent accuracy, the judged dimensions and
figure overlap; the highest composite is the recommended model. A **value index**
(composite per USD of estimated cost) highlights the best quality-for-cost.

**3. Agentic tool-selection accuracy** *(every backend)* — runs the **agentic**
orchestrator over labelled cases (`TOOL_SELECTION_CASES`) and checks whether the
model **itself** chooses the right tool (or no tool for clarify/decline). The
orchestrator is backend-appropriate: `AgenticOrchestrator` (Claude Agent SDK) for
`claude_code`, `ToolCallingOrchestrator` (native `bind_tools`) for `azure` /
`providers`. This is the model-driven counterpart
to intent classification — see [orchestration.md](orchestration.md). It is
tracked per round as a `Tool sel.` column (summary + history) and a per-question
**ToolSelection** sheet / HTML section. Control it with
`--tool-selection-sample N` (default = all cases) or `--no-tool-selection` to
skip. It is **not** folded into the composite, so composite stays comparable
across backends; report it alongside groundedness as a separate dimension.

## Artifacts (per round)

Each run writes a **timestamped** set plus a **`_latest`** set, and appends to a
cumulative history — all under `results/` (gitignored):

| File | Contents |
|---|---|
| `model_eval_<ts>.md` | Markdown summary table + recommendation |
| `model_eval_<ts>.html` | Report: SVG composite chart · summary (+ value index) · **confusion matrix** + per-intent accuracy · per-question intent table (misclassifications flagged) · per-question responses with answers and expandable tool-output |
| `model_eval_<ts>.xlsx` | 5 sheets — **Summary · Intent · Responses · Confusion · Trend** — with conditional formatting (PASS/FAIL, score colour-scales) and tool params/output audit columns |
| `model_eval_<ts>.json` | Machine-readable: summary + every per-question record |
| `model_eval_history.csv` | One row per model per round; feeds the cross-round **Trend** sheet |

## Backends

| `--backend` | Models | Auth |
|---|---|---|
| `claude_code` (default) | Claude Opus / Sonnet / Haiku | Claude Code subscription quota — local CLI session, or `CLAUDE_CODE_OAUTH_TOKEN` in CI (keep `ANTHROPIC_API_KEY` unset) |
| `azure` | Azure AI Foundry deployments (`AZURE_MODELS`; **auto-skips undeployed**) | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` |
| `google` | Gemini (`GOOGLE_MODELS`) | `GOOGLE_API_KEY` |
| `copilot` | Models behind a local Anthropic-style proxy (`COPILOT_MODELS`; **auto-skips unserved**) | `COPILOT_PROXY_BASE_URL` (default `localhost:4000`) + `COPILOT_PROXY_API_KEY` |
| `providers` | GPT-4o, Claude Sonnet (extend in `PROVIDER_MODELS`) | Provider API keys |
| `matrix` | The cross-vendor `MODEL_MATRIX` (OpenAI/Anthropic/Google × cheap/medium/strong); **auto-skips unreachable** | per-model (Azure / subscription / Google key) |

See the [test matrix](model-landscape.md#test-matrix-prepared-for-future-runs)
for the candidate models and how to light up each vendor tier.

The `azure` backend "keeps all models open": it probes every candidate in
`AZURE_MODELS` and silently skips any not deployed in the Foundry resource, so
deploying more models lights them up with no code change. Tool-selection on
`azure`/`providers` uses the native `ToolCallingOrchestrator` (`bind_tools`);
on `claude_code` it uses the Claude Agent SDK `AgenticOrchestrator`.

Example `azure` round (only `gpt-4o` deployed today): intent 83%, **tool-selection
100%**, groundedness 5.0/5, composite 0.918, value 40.4 — far cheaper/faster
(~2s/turn) than the Claude rounds; tracked alongside them in the Trend.

Because grounding comes from `tool_output` (not native tool-calling), the eval
is uniform across every backend — no provider needs special handling.

> **Current scope:** the eval has been run **Claude-only** (opus / sonnet / haiku
> on the subscription quota). GPT and Gemini need metered API keys; the
> `--backend providers` path is ready for them (add a `google_genai` branch in
> `build_llm` + prices in `app/metrics.py` for Gemini).

## Results

Latest round (2026-06-10, 12 intent + 4 grounded cases):

| Model | Intent acc. | Groundedness /5 | Figure overlap | Relevance /5 | Format /5 | Avg latency | Cost (USD) | Value | Composite |
|---|---|---|---|---|---|---|---|---|---|
| **opus** | 100% | 4.0 | 88% | 5.0 | 5.0 | 15.5s | $0.374 | 2.5 | **0.937** |
| sonnet | 100% | 4.0 | 81% | 5.0 | 5.0 | 18.7s | $0.058 | 15.6 | 0.913 |
| haiku | 100% | 3.5 | 81% | 5.0 | 4.8 | 19.0s | $0.039 | 22.8 | 0.897 |

All three reached **100% intent accuracy**. Composites were stable across three
rounds (0.952→0.930→0.937 for opus); intent accuracy converged to 100% for every
model by round 2 (Haiku's only early miss was `CLARIFICATION → OPTIMIZER_RUN`,
visible in the confusion matrix).

**Decision:** **Opus** is the pinned production model (`LLM_MODEL=claude-opus-4-8`)
on top composite; **Haiku** is the documented cost-sensitive fallback (~9× the
quality-per-dollar). See the [model landscape](model-landscape.md) for the wider
candidate field.

## Tuning

- `--intent-sample N` — number of intent cases to test (`0` = all 60). Lower it
  to save quota.
- Edit `CLAUDE_CODE_MODELS` / `PROVIDER_MODELS` in the script to change the
  candidate set.
- Expand `intent_dataset.json` and `GROUNDED_CASES` for larger mass runs.

## Related

This evaluation scores the **deterministic** orchestrator's intent
classification (which the router maps 1:1 to a tool). For the **agentic**
orchestrator — where the model decides the tool itself — see the
tool-selection test in [orchestration.md](orchestration.md).
