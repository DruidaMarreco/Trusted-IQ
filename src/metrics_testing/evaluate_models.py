"""TradeIQ TPO model evaluation — compare LLMs on the GenAI Sales Assistant flow.

For each candidate model it runs the real thin-orchestrator prompts:
  1. Intent classification (PROMPT-001) over the ground-truth dataset -> accuracy.
  2. Grounded response generation (PROMPT-002) from mock tool output -> judged on
     groundedness, relevance and format (LLM-as-judge), plus a deterministic
     figure-overlap groundedness signal.

Writes a comparison report so the best model(s) can be chosen.

Backend defaults to 'claude_code' (Claude Code subscription quota); use
'--backend providers' to compare metered provider models instead.

    uv run python scripts/evaluate_models.py --output results/model_eval.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.eval import classified_intent, groundedness_overlap
from app.prompts import (
    INTENT_SYSTEM_PROMPT,
    INTENT_USER_TEMPLATE,
    RESPONSE_SYSTEM_PROMPT,
    RESPONSE_USER_TEMPLATE,
)
from app.tpo_tools import route_to_tool

INTENT_DATASET_PATH = Path(__file__).parent.parent / "tests" / "data" / "intent_dataset.json"

# Candidate models per backend.
CLAUDE_CODE_MODELS = ["opus", "sonnet", "haiku"]
PROVIDER_MODELS = [("openai", "gpt-4o"), ("anthropic", "claude-sonnet-4-6")]

# Grounded response cases — each query + the params used to fetch its tool output.
GROUNDED_CASES: list[dict[str, Any]] = [
    {
        "query": "Why did you recommend the Easter display for Tesco?",
        "intent": "DATA_QUERY",
        "params": {"account": "Tesco"},
    },
    {"query": "Show me the recommendations for Carrefour.", "intent": "DATA_QUERY", "params": {"account": "Carrefour"}},
    {
        "query": "What are the best promo options for my remaining £80k budget?",
        "intent": "OPTIMIZER_RUN",
        "params": {"budget_remaining": 80000, "objective": "maximise ROI"},
    },
    {"query": "Give me options for a £40k budget.", "intent": "OPTIMIZER_RUN", "params": {"budget_remaining": 40000}},
]

JUDGE_PROMPT = """You are evaluating a TradeIQ Sales Assistant answer for a CPG commercial team.

The tool output below is the ONLY source of facts the answer may use:
{tool_output}

User query: "{query}"

Assistant answer:
{answer}

Score each dimension 1-5 (5 = best) and return ONLY a JSON object:
{{"groundedness": <1-5>, "relevance": <1-5>, "format": <1-5>, "notes": "<one sentence>"}}
- groundedness: every fact/number in the answer is supported by the tool output; NO fabrication.
- relevance: directly answers the user's query.
- format: concise business language, key figures in bold, a suggested next step."""

ACCOUNT_SCOPE = "All UK & EU grocery accounts"
PLANNING_PERIOD = "FY2025"

_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>TradeIQ TPO — Model Evaluation</title>
<style>
body {{ font-family: system-ui, "Segoe UI", Arial, sans-serif; margin: 2rem; color: #1a1a1a; }}
h1 {{ font-size: 1.4rem; margin-bottom: .25rem; }}
.meta {{ color: #666; margin-bottom: 1rem; }}
table {{ border-collapse: collapse; width: 100%; max-width: 920px; }}
th, td {{ border: 1px solid #ddd; padding: .5rem .75rem; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
thead {{ background: #0b5fff; color: #fff; }}
tr.best {{ background: #e8f5e9; }}
.rec {{ margin-top: 1rem; padding: .75rem; background: #e8f5e9; border-left: 4px solid #2e7d32; }}
small {{ color: #888; }}
</style></head><body>
<h1>TradeIQ TPO — Model Evaluation</h1>
<div class="meta">Intent cases: {intent_n} &middot; Grounded response cases: {n_cases}</div>
<table><thead><tr>
<th>Model</th><th>Intent acc.</th><th>Groundedness /5</th><th>Figure overlap</th>
<th>Relevance /5</th><th>Format /5</th><th>Composite</th></tr></thead>
<tbody>
{rows}
</tbody></table>
<div class="rec"><strong>Recommended:</strong> {best} (composite {composite:.3f})</div>
<p><small>Groundedness = answer uses only tool output (LLM judge + figure-overlap check).</small></p>
</body></html>
"""


@dataclass
class ModelScore:
    name: str
    intent_correct: int = 0
    intent_total: int = 0
    groundedness: list[float] = field(default_factory=list)
    relevance: list[float] = field(default_factory=list)
    fmt: list[float] = field(default_factory=list)
    figure_overlap: list[float] = field(default_factory=list)

    @property
    def intent_accuracy(self) -> float:
        return self.intent_correct / self.intent_total if self.intent_total else 0.0

    @staticmethod
    def _avg(xs: list[float]) -> float:
        return statistics.mean(xs) if xs else 0.0

    @property
    def composite(self) -> float:
        """Overall score (0-1): intent accuracy + judged dims + figure overlap."""
        judged = self._avg(self.groundedness + self.relevance + self.fmt) / 5
        return statistics.mean([self.intent_accuracy, judged, self._avg(self.figure_overlap)])


def _parse_judge(text: str) -> dict[str, float]:
    try:
        start = text.index("{")
        data = json.loads(text[start : text.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {}
    out: dict[str, float] = {}
    for key in ("groundedness", "relevance", "format"):
        try:
            out[key] = float(data[key])
        except (KeyError, TypeError, ValueError):
            out[key] = 0.0
    return out


async def _complete(llm: BaseChatModel, system: str, user: str) -> str:
    resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
    return str(resp.content)


async def _evaluate_model(
    name: str,
    llm: BaseChatModel,
    judge: BaseChatModel,
    intent_cases: list[dict[str, str]],
) -> ModelScore:
    score = ModelScore(name=name)

    # 1. Intent classification accuracy.
    for case in intent_cases:
        user = INTENT_USER_TEMPLATE.format(
            query=case["query"], history="[]", account_scope=ACCOUNT_SCOPE, planning_period=PLANNING_PERIOD
        )
        try:
            text = await _complete(llm, INTENT_SYSTEM_PROMPT, user)
        except Exception as exc:
            print(f"  intent ERROR ({case['query'][:40]}): {exc}")
            continue
        score.intent_total += 1
        if classified_intent(text) == case["expected"]:
            score.intent_correct += 1
    print(f"  intent accuracy: {score.intent_accuracy * 100:.1f}% ({score.intent_correct}/{score.intent_total})")

    # 2. Grounded response generation, judged.
    for case in GROUNDED_CASES:
        tool_name, tool_desc, tool_output = route_to_tool(str(case["intent"]), dict(case["params"]))
        user = RESPONSE_USER_TEMPLATE.format(
            query=case["query"],
            intent=case["intent"],
            tool_name=tool_name,
            tool_description=tool_desc,
            tool_output=json.dumps(tool_output, indent=2),
            account_scope=ACCOUNT_SCOPE,
            planning_period=PLANNING_PERIOD,
        )
        try:
            answer = await _complete(llm, RESPONSE_SYSTEM_PROMPT, user)
        except Exception as exc:
            print(f"  response ERROR ({case['query'][:40]}): {exc}")
            continue

        score.figure_overlap.append(groundedness_overlap(answer, tool_output))
        judged = _parse_judge(
            await _complete(
                judge,
                "You are a strict, fair evaluator. Return only JSON.",
                JUDGE_PROMPT.format(tool_output=json.dumps(tool_output, indent=2), query=case["query"], answer=answer),
            )
        )
        score.groundedness.append(judged.get("groundedness", 0.0))
        score.relevance.append(judged.get("relevance", 0.0))
        score.fmt.append(judged.get("format", 0.0))
    print(
        f"  groundedness: judge={score._avg(score.groundedness):.1f}/5 "
        f"figure-overlap={score._avg(score.figure_overlap) * 100:.0f}%"
    )
    return score


def _render_report(scores: list[ModelScore], intent_n: int) -> str:
    lines = [
        "# TradeIQ TPO — Model Evaluation",
        "",
        f"Intent cases: {intent_n} · Grounded response cases: {len(GROUNDED_CASES)}",
        "",
        "| Model | Intent acc. | Groundedness (judge /5) | Figure overlap | Relevance /5 | Format /5 | Composite |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in sorted(scores, key=lambda x: -x.composite):
        lines.append(
            f"| **{s.name}** | {s.intent_accuracy * 100:.1f}% | {s._avg(s.groundedness):.1f} "
            f"| {s._avg(s.figure_overlap) * 100:.0f}% | {s._avg(s.relevance):.1f} "
            f"| {s._avg(s.fmt):.1f} | {s.composite:.3f} |"
        )
    if scores:
        best = max(scores, key=lambda x: x.composite)
        lines += ["", f"**Recommended:** {best.name} (composite {best.composite:.3f})."]
    return "\n".join(lines) + "\n"


def _render_html(scores: list[ModelScore], intent_n: int) -> str:
    ranked = sorted(scores, key=lambda x: -x.composite)
    if not ranked:
        return "<!doctype html><html><body><p>No results.</p></body></html>\n"
    best = ranked[0]
    row_list: list[str] = []
    for s in ranked:
        cls = "best" if s.name == best.name else ""
        row_list.append(
            f'<tr class="{cls}"><td>{s.name}</td>'
            f"<td>{s.intent_accuracy * 100:.1f}%</td>"
            f"<td>{s._avg(s.groundedness):.1f}</td>"
            f"<td>{s._avg(s.figure_overlap) * 100:.0f}%</td>"
            f"<td>{s._avg(s.relevance):.1f}</td>"
            f"<td>{s._avg(s.fmt):.1f}</td>"
            f"<td><strong>{s.composite:.3f}</strong></td></tr>"
        )
    return _HTML_TEMPLATE.format(
        intent_n=intent_n,
        n_cases=len(GROUNDED_CASES),
        rows="\n".join(row_list),
        best=best.name,
        composite=best.composite,
    )


async def run_evaluation(intent_sample: int, output_path: Path, backend: str) -> None:
    from app.llm_factory import build_llm

    dataset: list[dict[str, str]] = json.loads(INTENT_DATASET_PATH.read_text(encoding="utf-8"))
    intent_cases = dataset[:intent_sample] if intent_sample > 0 else dataset
    print(f"Intent cases: {len(intent_cases)} | Grounded cases: {len(GROUNDED_CASES)} | backend: {backend}")

    if backend == "claude_code":
        models = [(m, build_llm(model=m, provider="claude_code")) for m in CLAUDE_CODE_MODELS]
        judge = build_llm(model="haiku", provider="claude_code")
    else:
        models = [(name, build_llm(model=name, provider=prov)) for prov, name in PROVIDER_MODELS]
        judge = build_llm(model="gpt-4o-mini", provider="openai")

    scores: list[ModelScore] = []
    for name, llm in models:
        print(f"\n▶ {name}")
        scores.append(await _evaluate_model(name, llm, judge, intent_cases))

    report = _render_report(scores, len(intent_cases))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    html_path = output_path.with_suffix(".html")
    html_path.write_text(_render_html(scores, len(intent_cases)), encoding="utf-8")
    print(f"\n✅ Reports saved → {output_path} and {html_path}\n")
    print(report)


def main() -> None:
    # Windows consoles default to cp1252 and choke on the report's unicode
    # (£, ▶, ·, …). Force UTF-8 output so the eval runs everywhere.
    cast(Any, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="TradeIQ TPO model evaluation")
    parser.add_argument("--intent-sample", type=int, default=24, help="Number of intent cases to test (0 = all)")
    parser.add_argument("--output", type=Path, default=Path("results/model_eval.md"), help="Output markdown file")
    parser.add_argument("--backend", choices=["claude_code", "providers"], default="claude_code")
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.intent_sample, args.output, args.backend))


if __name__ == "__main__":
    main()
