"""Agent orchestrator — the thin-orchestrator flow for the TradeIQ Sales Assistant.

    classify intent (PROMPT-001)  ->  route to a tool (tpo_tools)  ->  grounded
    response (PROMPT-002)

Provider-agnostic: the chat model is injected (Azure OpenAI GPT-4o in
production via build_llm). Extensible: new intents/tools are added in
tpo_tools.route_to_tool; this control flow stays the same — the seed of the
wider agentic framework.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import Settings
from app.config import settings as _default_settings
from app.eval import parse_intent_json
from app.metrics import CallMetrics, TurnMetrics, estimate_cost
from app.prompts import (
    INTENT_SYSTEM_PROMPT,
    INTENT_USER_TEMPLATE,
    INTENTS,
    RESPONSE_SYSTEM_PROMPT,
    RESPONSE_USER_TEMPLATE,
)
from app.tpo_tools import route_to_tool

logger = structlog.get_logger(__name__)

OUT_OF_SCOPE_REPLY = (
    "I can only help with trade promotion planning, optimisation and reporting. "
    "Could you rephrase your question in that context?"
)
DEFAULT_CLARIFY = "Could you add a bit more detail — which account, period, budget or objective?"


@dataclass
class OrchestratorResult:
    """Outcome of one orchestration turn."""

    answer: str
    intent: str
    confidence: float = 0.0
    tool: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    tool_output: dict[str, Any] = field(default_factory=dict)
    metrics: TurnMetrics = field(default_factory=TurnMetrics)


class OrchestratorAgent:
    """Classifies intent, routes to the right tool, and grounds the answer."""

    def __init__(self, llm: BaseChatModel, cfg: Settings | None = None) -> None:
        self._llm = llm
        self._cfg = cfg or _default_settings

    def _model_name(self) -> str:
        return str(getattr(self._llm, "model", None) or getattr(self._llm, "model_name", None) or self._cfg.llm_model)

    async def _complete(self, system: str, user: str) -> tuple[str, CallMetrics]:
        start = time.perf_counter()
        response = await self._llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(usage.get("input_tokens", 0)) if isinstance(usage, dict) else 0
        output_tokens = int(usage.get("output_tokens", 0)) if isinstance(usage, dict) else 0
        model = self._model_name()
        call = CallMetrics(
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(estimate_cost(model, input_tokens, output_tokens), 6),
        )
        logger.info(
            "llm_call",
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=call.cost_usd,
        )
        return str(response.content), call

    async def run(
        self,
        query: str,
        *,
        history: str = "[]",
        account_scope: str = "",
        planning_period: str = "",
    ) -> OrchestratorResult:
        """Run one turn: classify -> route -> ground."""
        metrics = TurnMetrics()
        # 1. Classify intent.
        classify_user = INTENT_USER_TEMPLATE.format(
            query=query,
            history=history,
            account_scope=account_scope or "n/a",
            planning_period=planning_period or "n/a",
        )
        raw, classify_call = await self._complete(INTENT_SYSTEM_PROMPT, classify_user)
        metrics.add(classify_call)
        data = parse_intent_json(raw)
        intent = str(data.get("intent", "")).strip().upper()
        confidence = float(data.get("confidence", 0.0) or 0.0)
        params = data.get("extracted_params") or {}
        if not isinstance(params, dict):
            params = {}
        logger.info("intent_classified", intent=intent, confidence=confidence)

        # 2a. Non-tool intents resolve immediately.
        if intent == "CLARIFICATION":
            question = str(data.get("clarifying_question") or DEFAULT_CLARIFY)
            logger.info("turn_complete", intent="CLARIFICATION", **metrics.as_dict())
            return OrchestratorResult(
                answer=question, intent="CLARIFICATION", confidence=confidence, params=params, metrics=metrics
            )
        if intent not in INTENTS or intent == "OUT_OF_SCOPE":
            logger.info("turn_complete", intent="OUT_OF_SCOPE", **metrics.as_dict())
            return OrchestratorResult(
                answer=OUT_OF_SCOPE_REPLY, intent="OUT_OF_SCOPE", confidence=confidence, params=params, metrics=metrics
            )

        # 2b. Route to the tool for this intent.
        tool_name, tool_description, tool_output = route_to_tool(intent, params)
        logger.info("tool_invoked", tool=tool_name, intent=intent)

        # 3. Generate a grounded response from the tool output.
        respond_user = RESPONSE_USER_TEMPLATE.format(
            query=query,
            intent=intent,
            tool_name=tool_name,
            tool_description=tool_description,
            tool_output=json.dumps(tool_output, indent=2),
            account_scope=account_scope or "n/a",
            planning_period=planning_period or "n/a",
        )
        answer, respond_call = await self._complete(RESPONSE_SYSTEM_PROMPT, respond_user)
        metrics.add(respond_call)
        logger.info("turn_complete", intent=intent, tool=tool_name, **metrics.as_dict())
        return OrchestratorResult(
            answer=answer,
            intent=intent,
            confidence=confidence,
            tool=tool_name,
            params=params,
            tool_output=tool_output,
            metrics=metrics,
        )
