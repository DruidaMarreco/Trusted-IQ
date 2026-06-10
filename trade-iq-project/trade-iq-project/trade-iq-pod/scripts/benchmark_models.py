"""Benchmark script — compare LLM models for orchestrator role.

Measures per model:
  - Reasoning / decomposition quality (LLM-as-judge, 0-10)
  - Tool calling accuracy (correct tool + args, 0-1 per case)
  - Intent routing accuracy (% correct on intent_dataset.json)
  - End-to-end latency (seconds)
  - Cost per query (USD, based on published token prices)

Usage:
    python -m uv run python scripts/benchmark_models.py
    python -m uv run python scripts/benchmark_models.py --runs 5 --output results/benchmark.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    provider: str
    model: str
    display_name: str
    cost_input_per_1k: float   # USD per 1k input tokens
    cost_output_per_1k: float  # USD per 1k output tokens


MODELS: list[ModelSpec] = [
    # ------------------------------------------------------------------
    # OpenAI  (prices: platform.openai.com/docs/pricing)
    # ------------------------------------------------------------------
    # Frontier / best reasoning
    ModelSpec("openai", "gpt-5",       "GPT-5",       0.015,   0.060),
    # Best cost/quality balance
    ModelSpec("openai", "gpt-4o",      "GPT-4o",      0.0025,  0.010),
    # Cheapest, fast
    ModelSpec("openai", "gpt-4o-mini", "GPT-4o mini", 0.00015, 0.0006),

    # ------------------------------------------------------------------
    # Anthropic  (prices: platform.claude.com/docs/about-claude/models)
    # ------------------------------------------------------------------
    # Frontier — equivalent to GPT-5  ($5/$25 per MTok)
    ModelSpec("anthropic", "claude-opus-4-8",   "Claude Opus 4.8",   0.005,  0.025),
    # Mid-tier — equivalent to GPT-4o  ($3/$15 per MTok)
    ModelSpec("anthropic", "claude-sonnet-4-6", "Claude Sonnet 4.6", 0.003,  0.015),
    # Cheap/fast — equivalent to GPT-4o mini  ($1/$5 per MTok)
    ModelSpec("anthropic", "claude-haiku-4-5",  "Claude Haiku 4.5",  0.001,  0.005),

    # ------------------------------------------------------------------
    # Google Gemini  (prices: ai.google.dev/gemini-api/docs/pricing)
    # ------------------------------------------------------------------
    # Frontier — equivalent to GPT-5 / Opus 4.8
    ModelSpec("google_genai", "gemini-3.1-pro",   "Gemini 3.1 Pro",   0.00125, 0.010),
    # Mid-tier — equivalent to GPT-4o / Sonnet
    ModelSpec("google_genai", "gemini-3.5-flash",  "Gemini 3.5 Flash", 0.00030, 0.0025),
    # Cheap/fast — equivalent to GPT-4o mini / Haiku
    ModelSpec("google_genai", "gemini-3-flash",    "Gemini 3 Flash",   0.00015, 0.0006),
]

# ---------------------------------------------------------------------------
# Benchmark tasks
# ---------------------------------------------------------------------------

# --- Reasoning / decomposition tasks ---
REASONING_TASKS = [
    {
        "query": "Analyse the top 3 tech stocks by YTD performance, summarise risks, and suggest a rebalancing strategy.",
        "rubric": "Does the response decompose into: (1) data retrieval, (2) risk analysis, (3) strategy synthesis? Score 0-10.",
    },
    {
        "query": "A client has €500k in cash. Compare ETF vs direct equity allocation for a 5-year horizon.",
        "rubric": "Does the response address: allocation options, time horizon trade-offs, tax implications? Score 0-10.",
    },
    {
        "query": "Explain how rising interest rates affect bond portfolios and what actions an orchestrator should delegate.",
        "rubric": "Does the response correctly identify sub-tasks to delegate (macro analysis, portfolio impact, hedge options)? Score 0-10.",
    },
]

# --- Tool calling tasks ---
TOOL_SCHEMA = {
    "name": "get_stock_price",
    "description": "Fetch current stock price for a ticker symbol.",
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "Stock ticker, e.g. AAPL"},
            "currency": {"type": "string", "description": "ISO 4217 currency code"},
        },
        "required": ["ticker"],
    },
}

TOOL_TASKS = [
    {
        "query": "What is the current price of Apple stock in EUR?",
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "AAPL", "currency": "EUR"},
    },
    {
        "query": "Get me the Microsoft share price.",
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "MSFT"},
    },
    {
        "query": "Fetch NVDA price in GBP.",
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "NVDA", "currency": "GBP"},
    },
]

# --- Intent routing dataset path ---
INTENT_DATASET_PATH = Path(__file__).parent.parent / "tests" / "data" / "intent_dataset.json"

# Prompt sent to the model for intent classification
INTENT_PROMPT = """You are a query router. Classify the user query into exactly one of these intents:
- DATA_QUERY: the user wants to retrieve, list, or show data/numbers/values.
- EXPLAIN_SCENARIOS: the user wants an explanation, comparison, or reasoning about scenarios/plans.

Respond with ONLY the intent label, nothing else. No punctuation, no explanation.

Query: {query}
Intent:"""

# Judge prompt
JUDGE_PROMPT = """You are an impartial evaluator.

Task given to the model:
{query}

Rubric:
{rubric}

Model response:
{response}

Return ONLY a JSON object: {{"score": <0-10>, "reason": "<one sentence>"}}"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    model: str
    task_type: str
    task_index: int
    latency_s: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    score: float | None = None          # reasoning 0-10 | tool 0-1 | routing 0-1
    score_reason: str = ""
    raw_response: str = ""


@dataclass
class ModelSummary:
    spec: ModelSpec
    reasoning_scores: list[float] = field(default_factory=list)
    tool_scores: list[float] = field(default_factory=list)
    routing_scores: list[float] = field(default_factory=list)  # 0 or 1 per query
    latencies: list[float] = field(default_factory=list)
    total_cost_usd: float = 0.0

    @property
    def avg_reasoning(self) -> float:
        return statistics.mean(self.reasoning_scores) if self.reasoning_scores else 0.0

    @property
    def avg_tool(self) -> float:
        return statistics.mean(self.tool_scores) if self.tool_scores else 0.0

    @property
    def routing_accuracy(self) -> float:
        return statistics.mean(self.routing_scores) if self.routing_scores else 0.0

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def p95_latency(self) -> float:
        if len(self.latencies) < 2:
            return self.latencies[0] if self.latencies else 0.0
        sorted_l = sorted(self.latencies)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]


# ---------------------------------------------------------------------------
# Core benchmark logic
# ---------------------------------------------------------------------------

def _build_llm(spec: ModelSpec) -> BaseChatModel:
    """Import here to avoid hard dependency on all providers at module load."""
    from app.llm_factory import build_llm  # noqa: PLC0415
    return build_llm(model=spec.model, provider=spec.provider)


def _load_intent_dataset() -> list[dict[str, str]]:
    """Load intent routing dataset from tests/data/intent_dataset.json."""
    with INTENT_DATASET_PATH.open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate when SDK doesn't return usage (4 chars ≈ 1 token)."""
    return max(1, len(text) // 4)


def _compute_cost(spec: ModelSpec, input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1000 * spec.cost_input_per_1k
        + output_tokens / 1000 * spec.cost_output_per_1k
    )


async def _run_reasoning_task(
    llm: BaseChatModel,
    judge_llm: BaseChatModel,
    spec: ModelSpec,
    task: dict[str, str],
    idx: int,
) -> RunResult:
    start = time.perf_counter()
    response: AIMessage = await llm.ainvoke([HumanMessage(content=task["query"])])  # type: ignore[assignment]
    latency = time.perf_counter() - start

    raw = str(response.content)
    usage = getattr(response, "usage_metadata", None)
    input_tokens = usage.get("input_tokens", _estimate_tokens(task["query"])) if usage else _estimate_tokens(task["query"])
    output_tokens = usage.get("output_tokens", _estimate_tokens(raw)) if usage else _estimate_tokens(raw)
    cost = _compute_cost(spec, input_tokens, output_tokens)

    # LLM-as-judge
    judge_prompt = JUDGE_PROMPT.format(
        query=task["query"], rubric=task["rubric"], response=raw
    )
    judge_resp: AIMessage = await judge_llm.ainvoke([HumanMessage(content=judge_prompt)])  # type: ignore[assignment]
    score, reason = _parse_judge(str(judge_resp.content))

    return RunResult(
        model=spec.display_name,
        task_type="reasoning",
        task_index=idx,
        latency_s=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        score=score,
        score_reason=reason,
        raw_response=raw[:500],
    )


def _parse_judge(text: str) -> tuple[float, str]:
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        data = json.loads(text[start:end])
        return float(data.get("score", 0)), str(data.get("reason", ""))
    except (ValueError, KeyError, json.JSONDecodeError):
        return 0.0, "parse error"


async def _run_tool_task(
    llm: BaseChatModel,
    spec: ModelSpec,
    task: dict[str, str | dict[str, str]],
    idx: int,
) -> RunResult:
    from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: PLC0415

    tools = [convert_to_openai_tool(TOOL_SCHEMA)]
    llm_with_tools = llm.bind_tools(tools)  # type: ignore[attr-defined]

    start = time.perf_counter()
    response: AIMessage = await llm_with_tools.ainvoke([HumanMessage(content=str(task["query"]))])  # type: ignore[assignment]
    latency = time.perf_counter() - start

    raw = str(response.content)
    usage = getattr(response, "usage_metadata", None)
    input_tokens = usage.get("input_tokens", _estimate_tokens(str(task["query"]))) if usage else _estimate_tokens(str(task["query"]))
    output_tokens = usage.get("output_tokens", _estimate_tokens(raw)) if usage else _estimate_tokens(raw)
    cost = _compute_cost(spec, input_tokens, output_tokens)

    tool_calls = getattr(response, "tool_calls", [])
    score, reason = _evaluate_tool_call(tool_calls, task)

    return RunResult(
        model=spec.display_name,
        task_type="tool",
        task_index=idx,
        latency_s=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        score=score,
        score_reason=reason,
        raw_response=str(tool_calls)[:500],
    )


def _evaluate_tool_call(
    tool_calls: list[dict[str, object]],
    task: dict[str, str | dict[str, str]],
) -> tuple[float, str]:
    if not tool_calls:
        return 0.0, "no tool call made"

    call = tool_calls[0]
    called_tool = call.get("name", "")
    called_args: dict[str, str] = call.get("args", {})  # type: ignore[assignment]
    expected_tool = str(task["expected_tool"])
    expected_args: dict[str, str] = task["expected_args"]  # type: ignore[assignment]

    if called_tool != expected_tool:
        return 0.0, f"wrong tool: got {called_tool}"

    matches = sum(
        1 for k, v in expected_args.items()
        if str(called_args.get(k, "")).upper() == str(v).upper()
    )
    score = matches / len(expected_args)
    reason = f"{matches}/{len(expected_args)} args correct"
    return score, reason


async def _run_routing_task(
    llm: BaseChatModel,
    spec: ModelSpec,
    item: dict[str, str],
    idx: int,
) -> RunResult:
    """Classify a single query and compare to expected intent label."""
    prompt = INTENT_PROMPT.format(query=item["query"])

    start = time.perf_counter()
    response: AIMessage = await llm.ainvoke([HumanMessage(content=prompt)])  # type: ignore[assignment]
    latency = time.perf_counter() - start

    raw = str(response.content).strip().upper()
    # Normalise — model may return label with trailing punctuation or spaces
    predicted = raw.split()[0] if raw else ""
    expected = item["expected"].strip().upper()
    correct = 1.0 if predicted == expected else 0.0
    reason = f"predicted={predicted} expected={expected}"

    usage = getattr(response, "usage_metadata", None)
    input_tokens = usage.get("input_tokens", _estimate_tokens(prompt)) if usage else _estimate_tokens(prompt)
    output_tokens = usage.get("output_tokens", _estimate_tokens(raw)) if usage else _estimate_tokens(raw)
    cost = _compute_cost(spec, input_tokens, output_tokens)

    return RunResult(
        model=spec.display_name,
        task_type="routing",
        task_index=idx,
        latency_s=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        score=correct,
        score_reason=reason,
        raw_response=raw[:100],
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _render_markdown(
    summaries: list[ModelSummary],
    runs: int,
    timestamp: str,
    intent_dataset: list[dict[str, str]],
) -> str:
    n_routing = len(intent_dataset)
    # Count per-intent in dataset for report context
    intent_counts: dict[str, int] = {}
    for item in intent_dataset:
        intent_counts[item["expected"]] = intent_counts.get(item["expected"], 0) + 1

    lines: list[str] = [
        "# LLM Orchestrator Benchmark Report",
        f"\n**Generated:** {timestamp}  ",
        f"**Runs per task:** {runs}  ",
        f"**Reasoning tasks:** {len(REASONING_TASKS)}  ",
        f"**Tool calling tasks:** {len(TOOL_TASKS)}  ",
        f"**Routing queries:** {n_routing} "
        + " / ".join(f"{v} {k}" for k, v in sorted(intent_counts.items())),
        "\n---\n",
        "## Summary",
        "",
        "| Model | Reasoning (0-10) | Tool Accuracy (%) | Routing Accuracy (%) | Avg Latency (s) | p95 Latency (s) | Total Cost (USD) |",
        "|---|---|---|---|---|---|---|",
    ]

    for s in sorted(summaries, key=lambda x: -(x.avg_reasoning + x.routing_accuracy * 10) / 2):
        lines.append(
            f"| **{s.spec.display_name}** "
            f"| {s.avg_reasoning:.1f} "
            f"| {s.avg_tool * 100:.0f}% "
            f"| {s.routing_accuracy * 100:.0f}% "
            f"| {s.avg_latency:.2f}s "
            f"| {s.p95_latency:.2f}s "
            f"| ${s.total_cost_usd:.4f} |"
        )

    lines += [
        "\n---\n",
        "## Cost vs Quality",
        "",
        "| Model | Cost/query (USD) | Reasoning (0-10) | Routing (%) | Value index* |",
        "|---|---|---|---|---|",
    ]
    for s in summaries:
        n_queries = len(REASONING_TASKS) + len(TOOL_TASKS) + n_routing
        cost_per_query = s.total_cost_usd / max(n_queries, 1)
        # Combined quality: weight reasoning 50%, routing 50%
        combined = (s.avg_reasoning / 10 + s.routing_accuracy) / 2
        value = combined / max(cost_per_query * 1000, 0.001)
        lines.append(
            f"| {s.spec.display_name} "
            f"| ${cost_per_query:.5f} "
            f"| {s.avg_reasoning:.1f} "
            f"| {s.routing_accuracy * 100:.0f}% "
            f"| {value:.0f} |"
        )

    lines += [
        "",
        "_* Value index = combined quality / (cost per query × 1000). Higher = better value._",
        "\n---\n",
        "## Intent Routing Results",
        "",
        f"Dataset: `{INTENT_DATASET_PATH.name}` — {n_routing} queries",
        "",
        "### Accuracy per model",
        "",
        "| Model | Correct | Total | Accuracy | Avg Latency (s) |",
        "|---|---|---|---|---|",
    ]

    for s in sorted(summaries, key=lambda x: -x.routing_accuracy):
        correct = sum(s.routing_scores)
        total = len(s.routing_scores)
        avg_lat = statistics.mean(
            r.latency_s for r in s.__dict__.get("_runs", []) if r.task_type == "routing"
        ) if any(r.task_type == "routing" for r in s.__dict__.get("_runs", [])) else 0.0
        lines.append(
            f"| {s.spec.display_name} "
            f"| {correct:.0f} "
            f"| {total} "
            f"| {s.routing_accuracy * 100:.1f}% "
            f"| {avg_lat:.2f}s |"
        )

    # Per-query breakdown for misclassified rows
    lines += [
        "",
        "### Misclassified queries (any model)",
        "",
        "| Query | Expected | " + " | ".join(s.spec.display_name for s in summaries) + " |",
        "|---|---|" + "|---|" * len(summaries),
    ]
    for idx, item in enumerate(intent_dataset):
        row_results = {
            s.spec.display_name: next(
                (r for r in s.__dict__.get("_runs", []) if r.task_type == "routing" and r.task_index == idx),
                None,
            )
            for s in summaries
        }
        any_wrong = any(
            r is not None and r.score == 0.0 for r in row_results.values()
        )
        if any_wrong:
            cells = []
            for s in summaries:
                r = row_results[s.spec.display_name]
                if r is None:
                    cells.append("—")
                elif r.score == 1.0:
                    cells.append("✅")
                else:
                    predicted = r.raw_response.strip().split()[0] if r.raw_response.strip() else "?"
                    cells.append(f"❌ `{predicted}`")
            lines.append(
                f"| {item['query'][:60]} "
                f"| `{item['expected']}` "
                f"| " + " | ".join(cells) + " |"
            )

    lines += [
        "\n---\n",
        "## Reasoning Task Details",
        "",
    ]
    for i, task in enumerate(REASONING_TASKS):
        lines.append(f"### Task R{i+1}")
        lines.append(f"> {task['query']}\n")
        lines.append("| Model | Score | Reason | Latency (s) |")
        lines.append("|---|---|---|---|")
        for s in summaries:
            scores = [r for r in s.__dict__.get("_runs", []) if r.task_type == "reasoning" and r.task_index == i]
            if scores:
                avg_s = statistics.mean(r.score or 0 for r in scores)
                avg_l = statistics.mean(r.latency_s for r in scores)
                lines.append(f"| {s.spec.display_name} | {avg_s:.1f} | {scores[0].score_reason} | {avg_l:.2f}s |")
        lines.append("")

    lines += [
        "## Tool Calling Task Details",
        "",
    ]
    for i, task in enumerate(TOOL_TASKS):
        lines.append(f"### Task T{i+1}")
        lines.append(f"> {task['query']}\n")
        lines.append("| Model | Accuracy | Reason | Latency (s) |")
        lines.append("|---|---|---|---|")
        for s in summaries:
            scores = [r for r in s.__dict__.get("_runs", []) if r.task_type == "tool" and r.task_index == i]
            if scores:
                avg_s = statistics.mean(r.score or 0 for r in scores)
                avg_l = statistics.mean(r.latency_s for r in scores)
                lines.append(f"| {s.spec.display_name} | {avg_s*100:.0f}% | {scores[0].score_reason} | {avg_l:.2f}s |")
        lines.append("")

    lines += [
        "---\n",
        "## Recommendation",
        "",
        "_Fill in after reviewing results above._",
        "",
        "| Use case | Recommended model | Reason |",
        "|---|---|---|",
        "| Orchestrator (production) | | |",
        "| Orchestrator (cost-sensitive) | | |",
        "| Subagents | | |",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def run_benchmark(runs: int, output_path: Path) -> None:
    from app.llm_factory import build_llm  # noqa: PLC0415

    intent_dataset = _load_intent_dataset()
    print(f"Loaded {len(intent_dataset)} routing queries from {INTENT_DATASET_PATH.name}")

    # Judge: cheap model for reasoning evaluation
    judge_llm = build_llm(model="gpt-4o-mini", provider="openai")

    summaries: list[ModelSummary] = []

    for spec in MODELS:
        print(f"\n▶ {spec.display_name}")
        summary = ModelSummary(spec=spec)
        summary.__dict__["_runs"] = []

        try:
            llm = _build_llm(spec)
        except Exception as e:
            print(f"  ✗ failed to build LLM: {e}")
            summaries.append(summary)
            continue

        for run_i in range(runs):
            # Reasoning tasks
            for i, task in enumerate(REASONING_TASKS):
                try:
                    r = await _run_reasoning_task(llm, judge_llm, spec, task, i)
                    summary.reasoning_scores.append(r.score or 0)
                    summary.latencies.append(r.latency_s)
                    summary.total_cost_usd += r.cost_usd
                    summary.__dict__["_runs"].append(r)
                    print(f"  R{i+1} run{run_i+1}: score={r.score:.1f} lat={r.latency_s:.2f}s cost=${r.cost_usd:.5f}")
                except Exception as e:
                    print(f"  R{i+1} run{run_i+1}: ERROR {e}")

            # Tool calling tasks
            for i, task in enumerate(TOOL_TASKS):
                try:
                    r = await _run_tool_task(llm, spec, task, i)
                    summary.tool_scores.append(r.score or 0)
                    summary.latencies.append(r.latency_s)
                    summary.total_cost_usd += r.cost_usd
                    summary.__dict__["_runs"].append(r)
                    print(f"  T{i+1} run{run_i+1}: acc={r.score*100:.0f}% lat={r.latency_s:.2f}s cost=${r.cost_usd:.5f}")
                except Exception as e:
                    print(f"  T{i+1} run{run_i+1}: ERROR {e}")

            # Intent routing — run all dataset queries (routing is deterministic,
            # so single run is sufficient but we respect --runs for consistency)
            if run_i == 0:  # run dataset once — no randomness in routing
                for i, item in enumerate(intent_dataset):
                    try:
                        r = await _run_routing_task(llm, spec, item, i)
                        summary.routing_scores.append(r.score or 0)
                        summary.latencies.append(r.latency_s)
                        summary.total_cost_usd += r.cost_usd
                        summary.__dict__["_runs"].append(r)
                    except Exception as e:
                        print(f"  Route q{i+1}: ERROR {e}")
                correct = sum(summary.routing_scores)
                total = len(summary.routing_scores)
                print(f"  Routing: {correct:.0f}/{total} correct ({correct/max(total,1)*100:.0f}%)")

        summaries.append(summary)

    # Render report
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    report = _render_markdown(summaries, runs, timestamp, intent_dataset)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\n✅ Report saved → {output_path}")

    # Console summary
    print("\n" + "=" * 75)
    print(f"{'Model':<22} {'Reasoning':>10} {'Tool%':>7} {'Routing%':>9} {'AvgLat':>8} {'Cost$':>10}")
    print("-" * 75)
    for s in sorted(summaries, key=lambda x: -(x.avg_reasoning + x.routing_accuracy * 10) / 2):
        print(
            f"{s.spec.display_name:<22} "
            f"{s.avg_reasoning:>10.1f} "
            f"{s.avg_tool*100:>6.0f}% "
            f"{s.routing_accuracy*100:>8.0f}% "
            f"{s.avg_latency:>7.2f}s "
            f"${s.total_cost_usd:>9.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM orchestrator benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Runs per task per model (default: 3)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/benchmark.md"),
        help="Output markdown file (default: results/benchmark.md)",
    )
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.runs, args.output))


if __name__ == "__main__":
    main()
