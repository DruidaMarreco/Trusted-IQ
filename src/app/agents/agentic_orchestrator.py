"""Agentic orchestrator — the model DECIDES whether/which tool to use.

Where ``OrchestratorAgent`` is a *thin* orchestrator (classify intent, then a
deterministic router picks the tool), this variant tests genuine **agentic tool
use**: Claude is given the CDT/ERDC tools plus a system prompt and autonomously
decides whether a tool is needed and which one to call, via the Claude Agent
SDK's native tool-use loop — on the Claude Code subscription quota (no API key).

What it lets us test: does the agent *understand* it needs a tool to complete
the task, and does it pick the right one? The tools it actually invokes are
captured in ``AgenticResult.tool_names``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.config import Settings
from app.config import settings as _default_settings
from app.metrics import CallMetrics, TurnMetrics, estimate_cost
from app.tools import cdt, erdc

logger = structlog.get_logger(__name__)

# Claude Code CLI model aliases; map full IDs (e.g. claude-opus-4-8) onto them.
_MODEL_ALIASES = {"opus", "sonnet", "haiku"}

AGENTIC_SYSTEM_PROMPT = """You are the TradeIQ TPO Sales Assistant for CPG commercial teams \
(trade promotion planning, optimisation and reporting for UK & EU grocery accounts).

You have two tools:
- text_to_sql_lookup: retrieve EXISTING recommendations or performance data for an account \
(use for "why was X recommended", "show/list/rank past promos", actuals vs predicted, ROI/uplift history).
- optimizer_run: generate NEW or re-optimised promotion options within a budget/objective \
(use for "best options for £Xk", "optimise my plan", "run a scenario").

Decide for yourself whether a tool is needed, and prefer acting over asking — \
call a tool whenever you have enough to proceed:
- About existing data AND an account is named -> call text_to_sql_lookup. \
The account alone is enough; do NOT ask for the SKU or period first.
- A request to generate / optimise / re-optimise options, or "best options" -> call optimizer_run. \
It has a sensible default budget, so call it even if the exact budget is unspecified; \
pass budget_remaining / objective only when the user gave them.
- Genuinely vague with NO account and NO budget/objective (e.g. "show me the options") -> \
DO NOT call a tool; ask ONE concise clarifying question.
- Not about trade promotion -> DO NOT call a tool; politely decline.

Ground your final answer ONLY in tool output; never invent figures. Be concise, bold the key figures, \
and suggest a next step."""

_CDT_SCHEMA = {"account": str, "time_period": str, "sku": str, "question": str}
_ERDC_SCHEMA = {"budget_remaining": int, "objective": str, "account": str}


def _coerce_model(model: str) -> str:
    """Map a configured model name onto a Claude Code CLI alias."""
    if model in _MODEL_ALIASES:
        return model
    for alias in _MODEL_ALIASES:
        if alias in model:  # e.g. "claude-opus-4-8" -> "opus"
            return alias
    return "sonnet"


@dataclass
class AgenticResult:
    """Outcome of one agentic turn, including the tools the agent chose to call."""

    answer: str
    tools_used: list[dict[str, Any]] = field(default_factory=list)
    num_turns: int = 0
    metrics: TurnMetrics = field(default_factory=TurnMetrics)

    @property
    def tool_names(self) -> list[str]:
        """Bare TPO tool names the agent invoked (mcp__tpo__optimizer_run -> optimizer_run).

        Excludes the Agent SDK's built-in ``ToolSearch`` discovery step, which
        surfaces our deferred MCP tools but is not a domain decision.
        """
        names = [str(t.get("name", "")) for t in self.tools_used]
        return [n.split("__")[-1] for n in names if n.startswith("mcp__tpo__")]


class AgenticOrchestrator:
    """Hands Claude the TPO tools and lets it decide what to call (Agent SDK)."""

    def __init__(self, model: str | None = None, cfg: Settings | None = None) -> None:
        self._cfg = cfg or _default_settings
        self._model = _coerce_model(model or self._cfg.llm_model)

    def _build_tools(self) -> list[Any]:
        """Define the CDT/ERDC tools as in-process Agent SDK tools (live-or-mock)."""
        from claude_agent_sdk import tool

        cfg = self._cfg

        @tool("text_to_sql_lookup", "Retrieve existing TPO recommendations or performance for an account.", _CDT_SCHEMA)
        async def text_to_sql_lookup(args: dict[str, Any]) -> dict[str, Any]:
            params = {"account": args.get("account"), "time_period": args.get("time_period"), "sku": args.get("sku")}
            output = await cdt.text_to_sql_lookup(params, cfg, question=str(args.get("question", "")))
            return {"content": [{"type": "text", "text": json.dumps(output)}]}

        @tool("optimizer_run", "Generate or re-optimise promotion options within a budget/objective.", _ERDC_SCHEMA)
        async def optimizer_run(args: dict[str, Any]) -> dict[str, Any]:
            params = {
                "budget_remaining": args.get("budget_remaining"),
                "objective": args.get("objective"),
                "account": args.get("account"),
            }
            output = await erdc.optimizer_run(params, cfg)
            return {"content": [{"type": "text", "text": json.dumps(output)}]}

        return [text_to_sql_lookup, optimizer_run]

    async def run(self, query: str, *, account_scope: str = "", planning_period: str = "") -> AgenticResult:
        """Run one agentic turn: Claude decides which (if any) tool to call."""
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            TextBlock,
            ToolUseBlock,
            create_sdk_mcp_server,
        )
        from claude_agent_sdk import query as sdk_query

        server = create_sdk_mcp_server("tpo", tools=self._build_tools())
        context = ""
        if account_scope or planning_period:
            context = f"\n\nContext — accounts: {account_scope or 'n/a'}; planning period: {planning_period or 'n/a'}."
        options = ClaudeAgentOptions(
            model=self._model,
            system_prompt=AGENTIC_SYSTEM_PROMPT + context,
            mcp_servers={"tpo": server},
            allowed_tools=["mcp__tpo__text_to_sql_lookup", "mcp__tpo__optimizer_run"],
            permission_mode="bypassPermissions",
            setting_sources=[],  # don't load repo/user CLAUDE.md or settings — isolate the agent
            max_turns=4,
        )

        tools_used: list[dict[str, Any]] = []
        answer = ""
        input_tokens = output_tokens = num_turns = 0
        cost_usd = 0.0

        start = time.perf_counter()
        async for message in sdk_query(prompt=query, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        tools_used.append({"name": block.name, "input": block.input})
                        logger.info("agent_tool_call", tool=block.name, tool_input=block.input)
                    elif isinstance(block, TextBlock) and block.text.strip():
                        answer = block.text
            elif isinstance(message, ResultMessage):
                if message.result:
                    answer = str(message.result)
                num_turns = int(message.num_turns or 0)
                usage = message.usage if isinstance(message.usage, dict) else {}
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
                cost_usd = float(message.total_cost_usd or 0.0)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        if not cost_usd:
            cost_usd = round(estimate_cost(self._model, input_tokens, output_tokens), 6)
        metrics = TurnMetrics()
        metrics.add(
            CallMetrics(
                model=self._model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )
        )
        logger.info(
            "agentic_turn_complete", model=self._model, tools=tools_used, num_turns=num_turns, **metrics.as_dict()
        )
        return AgenticResult(answer=answer, tools_used=tools_used, num_turns=num_turns, metrics=metrics)
