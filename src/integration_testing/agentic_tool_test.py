"""Agentic tool-use test — does the agent decide to use the right tool?

Unlike the deterministic classify-then-route orchestrator, this exercises the
``AgenticOrchestrator``: Claude is given the CDT/ERDC tools and decides for
itself whether (and which) to call. For each scenario we check the tool it
actually invoked against the expected one, and report tool-selection accuracy.

Run (uses the Claude Code subscription quota — keep ANTHROPIC_API_KEY unset):
    AGENTIC_MODEL=sonnet uv run python src/integration_testing/agentic_tool_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, cast

from app.agents.agentic_orchestrator import AgenticOrchestrator

# scenario -> the tool the agent SHOULD choose (None = it should call no tool).
_SCENARIOS = [
    ("Why did you recommend the Easter display for Tesco?", "text_to_sql_lookup"),
    ("List my top performing promos for Carrefour last quarter.", "text_to_sql_lookup"),
    ("What are the best promo options for my remaining £80k budget at Tesco?", "optimizer_run"),
    ("Re-optimise my Aldi plan to hit a 1.5x uplift guideline.", "optimizer_run"),
    ("Show me the options.", None),
    ("What's the weather in London today?", None),
]


async def _run() -> int:
    model = os.environ.get("AGENTIC_MODEL", "sonnet")
    agent = AgenticOrchestrator(model=model)
    print(f"Agentic tool-use test — model: {model}\n")

    correct = 0
    for query, expected in _SCENARIOS:
        result = await agent.run(query)
        chosen = result.tool_names
        ok = len(chosen) == 0 if expected is None else expected in chosen
        correct += ok

        print(f"[{'PASS' if ok else 'FAIL'}] {query}")
        print(f"       expected: {expected or '(no tool)'} | chose: {chosen or '(none)'} | turns: {result.num_turns}")
        print(f"       answer: {result.answer[:160].replace(chr(10), ' ')}…\n")

    pct = correct / len(_SCENARIOS) * 100
    print(f"Tool-selection accuracy: {correct}/{len(_SCENARIOS)} ({pct:.0f}%)")
    return 0 if correct == len(_SCENARIOS) else 1


def main() -> None:
    cast(Any, sys.stdout).reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
