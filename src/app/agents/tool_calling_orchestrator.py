"""Native tool-calling orchestrator — provider-agnostic agentic tool use.

The model is given the CDT/ERDC tools via LangChain ``bind_tools`` (OpenAI-style
function calling) and **decides itself** whether and which to call. Unlike
``AgenticOrchestrator`` (Claude Agent SDK, subscription quota), this works with
**any tool-capable chat model** — Azure AI Foundry (gpt-4o, …), OpenAI,
Anthropic API — so it is the agentic path for the Azure-based deployment.

Captures the tools the model invoked (``ToolCallingResult.tool_names``) so the
same tool-selection accuracy can be measured across providers.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool

from app.config import Settings
from app.config import settings as _default_settings
from app.metrics import CallMetrics, TurnMetrics, estimate_cost
from app.tools import cdt, erdc

logger = structlog.get_logger(__name__)

TOOL_CALLING_SYSTEM_PROMPT = """You are the TradeIQ TPO Sales Assistant for CPG commercial teams \
(trade promotion planning, optimisation and reporting for UK & EU grocery accounts).

You have two tools:
- text_to_sql_lookup: retrieve EXISTING recommendations or performance data for an account.
- optimizer_run: generate NEW or re-optimised promotion options within a budget/objective.

Decide for yourself, and prefer acting over asking when you have enough to proceed:
- About existing data AND an account is named -> call text_to_sql_lookup (the account alone is enough).
- A request to generate / optimise / re-optimise options, or "best options" -> call optimizer_run.
- Genuinely vague with no account and no budget/objective -> do NOT call a tool; ask ONE clarifying question.
- Not about trade promotion -> do NOT call a tool; politely decline.

Ground your final answer ONLY in tool output; never invent figures. Be concise, bold key figures, \
and suggest a next step."""

_MAX_TURNS = 4


@dataclass
class ToolCallingResult:
    """Outcome of one native tool-calling turn."""

    answer: str
    tools_used: list[str] = field(default_factory=list)
    num_turns: int = 0
    metrics: TurnMetrics = field(default_factory=TurnMetrics)

    @property
    def tool_names(self) -> list[str]:
        return list(self.tools_used)


class ToolCallingOrchestrator:
    """Provider-agnostic agentic orchestrator using LangChain ``bind_tools``."""

    def __init__(self, llm: BaseChatModel, cfg: Settings | None = None) -> None:
        self._llm = llm
        self._cfg = cfg or _default_settings

    def _model_name(self) -> str:
        return str(getattr(self._llm, "model_name", None) or getattr(self._llm, "model", None) or self._cfg.llm_model)

    def _build_tools(self) -> list[BaseTool]:
        cfg = self._cfg

        @tool
        async def text_to_sql_lookup(
            account: str = "", time_period: str = "", sku: str = "", question: str = ""
        ) -> str:
            """Retrieve existing TPO recommendations or performance data for an account (CDT TextToSQL)."""
            params = {"account": account or None, "time_period": time_period or None, "sku": sku or None}
            return json.dumps(await cdt.text_to_sql_lookup(params, cfg, question=question))

        @tool
        async def optimizer_run(
            budget_remaining: int = 100_000, objective: str = "maximise ROI", account: str = ""
        ) -> str:
            """Generate or re-optimise promotion options within a budget/objective (ERDC Optimizer)."""
            params = {"budget_remaining": budget_remaining, "objective": objective, "account": account or None}
            return json.dumps(await erdc.optimizer_run(params, cfg))

        return [text_to_sql_lookup, optimizer_run]

    async def run(self, query: str, *, account_scope: str = "", planning_period: str = "") -> ToolCallingResult:
        """Run one turn: the model decides which (if any) tool to call, then grounds the answer."""
        tools = self._build_tools()
        tool_map = {t.name: t for t in tools}
        llm_with_tools = self._llm.bind_tools(tools)

        system = TOOL_CALLING_SYSTEM_PROMPT
        if account_scope or planning_period:
            system += f"\n\nContext — accounts: {account_scope or 'n/a'}; planning period: {planning_period or 'n/a'}."
        messages: list[BaseMessage] = [SystemMessage(content=system), HumanMessage(content=query)]

        metrics = TurnMetrics()
        tools_used: list[str] = []
        answer = ""
        num_turns = 0
        model = self._model_name()

        start = time.perf_counter()
        for _turn in range(_MAX_TURNS):
            num_turns += 1
            response = await llm_with_tools.ainvoke(messages)
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            start = time.perf_counter()
            usage = getattr(response, "usage_metadata", None)
            in_tok = int(usage.get("input_tokens", 0)) if isinstance(usage, dict) else 0
            out_tok = int(usage.get("output_tokens", 0)) if isinstance(usage, dict) else 0
            metrics.add(
                CallMetrics(
                    model=model,
                    latency_ms=latency_ms,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=round(estimate_cost(model, in_tok, out_tok), 6),
                )
            )
            messages.append(response)
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                text = getattr(response, "text", None)
                answer = text if isinstance(text, str) else str(response.content)
                break
            for call in tool_calls:
                name = call["name"]
                tools_used.append(name)
                logger.info("tool_call", tool=name, args=call.get("args"))
                target = tool_map.get(name)
                output = await target.ainvoke(call["args"]) if target else json.dumps({"error": f"unknown tool {name}"})
                messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

        logger.info(
            "tool_calling_turn_complete", model=model, tools=tools_used, num_turns=num_turns, **metrics.as_dict()
        )
        return ToolCallingResult(answer=answer, tools_used=tools_used, num_turns=num_turns, metrics=metrics)
