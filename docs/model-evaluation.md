# Model evaluation — choosing the orchestrator model

`src/metrics_testing/evaluate_models.py` implements the **[ML] Orchestrator Agent
Model Evaluation & Testing** task: it runs the real TradeIQ assistant flow for
each candidate model and scores them so we can pick the best one(s).

```bash
make evaluate
# or:
uv run python src/metrics_testing/evaluate_models.py --intent-sample 24 --backend claude_code
```

Outputs `results/model_eval.md` and `results/model_eval.html`.

## What it measures

For each candidate model the harness runs two evaluations:

### 1. Intent classification accuracy
Runs PROMPT-001 over the ground-truth dataset (`src/tests/data/intent_dataset.json`,
60 labelled queries across the four intents) and compares the predicted intent to
the label. Reported as accuracy.

### 2. Grounded response generation
For a set of grounded cases (query → tool output via `tpo_tools`), runs PROMPT-002
to generate an answer, then scores it on:

| Dimension | How |
|-----------|-----|
| **Groundedness** | LLM judge (1–5) **and** a deterministic figure-overlap check — every number in the answer must appear in the tool output (catches fabrication) |
| **Relevance** | LLM judge (1–5): does it answer the question? |
| **Format** | LLM judge (1–5): concise business language, bold figures, a next step |

A **composite** score (0–1) combines intent accuracy, the judged dimensions and
figure overlap; the highest composite is the recommended model.

## Backends

| `--backend` | Models | Auth |
|-------------|--------|------|
| `claude_code` (default) | Claude Opus / Sonnet / Haiku | Claude Code subscription quota — local CLI session, or `CLAUDE_CODE_OAUTH_TOKEN` in CI (keep `ANTHROPIC_API_KEY` unset) |
| `providers` | GPT-4o, Claude Sonnet (extend in `PROVIDER_MODELS`) | Provider API keys |

Because grounding comes from `tool_output` (not native tool-calling), the eval is
uniform across every backend — no provider needs special handling.

## Tuning

- `--intent-sample N` — number of intent cases to test (`0` = all 60). Lower it
  to save quota during quick runs.
- Edit `CLAUDE_CODE_MODELS` / `PROVIDER_MODELS` in the script to change the
  candidate set.
- Expand `intent_dataset.json` and `GROUNDED_CASES` for larger "mass" runs.

## Interpreting the report

The HTML report (`results/model_eval.html`) ranks models by composite score and
highlights the winner. Use it to choose:
- the **orchestrator** model (best intent accuracy + groundedness), and
- a **cost-sensitive** fallback (e.g. Haiku) if its groundedness is acceptable.
