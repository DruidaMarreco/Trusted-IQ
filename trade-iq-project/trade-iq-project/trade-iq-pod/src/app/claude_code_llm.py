"""LangChain chat model backed by the Claude Agent SDK (Claude Code).

Runs prompts through the local Claude Code installation so calls are billed to
the Claude Code SUBSCRIPTION QUOTA rather than a metered ANTHROPIC_API_KEY. This
lets the benchmark compare Claude models (Opus / Sonnet / Haiku) without
per-token API costs.

Authentication:
  - Local: uses the logged-in ``claude`` CLI session automatically.
  - Headless / CI: set ``CLAUDE_CODE_OAUTH_TOKEN`` (from ``claude setup-token``).
  - ``ANTHROPIC_API_KEY`` must be UNSET, or it takes precedence and you are
    billed against the metered API instead of the subscription.

Only single-turn text completion is supported (reasoning / classification).
Native tool-calling is not exposed — the Agent SDK is agentic, not single-shot.
"""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


def _messages_to_prompt(messages: list[BaseMessage]) -> str:
    """Flatten LangChain messages into a single prompt string."""
    return "\n\n".join(f"{getattr(m, 'type', 'user')}: {m.content}" for m in messages)


def _parse_query_messages(messages: list[Any]) -> tuple[str, int, int]:
    """Extract (text, input_tokens, output_tokens) from Agent SDK messages.

    Duck-typed so it works across SDK versions and is unit-testable without the
    SDK installed: a ResultMessage carries ``result`` + ``usage``; assistant
    messages carry a ``content`` list of blocks with ``text``.
    """
    text = ""
    input_tokens = 0
    output_tokens = 0
    for message in messages:
        result = getattr(message, "result", None)
        usage = getattr(message, "usage", None)
        if result is not None and usage is not None:
            text = str(result)
            if isinstance(usage, dict):
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
            continue
        content = getattr(message, "content", None)
        if isinstance(content, list):
            for block in content:
                block_text = getattr(block, "text", None)
                if block_text:
                    text = block_text
    return text, input_tokens, output_tokens


class ChatClaudeCode(BaseChatModel):
    """Chat model that proxies to Claude Code via the Claude Agent SDK."""

    model: str = "sonnet"

    @property
    def _llm_type(self) -> str:
        return "claude-code"

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Imported lazily so the SDK is only required when this backend is used.
        from claude_agent_sdk import ClaudeAgentOptions, query

        options = ClaudeAgentOptions(model=self.model, allowed_tools=[])
        collected = [m async for m in query(prompt=_messages_to_prompt(messages), options=options)]
        text, input_tokens, output_tokens = _parse_query_messages(collected)

        ai = AIMessage(
            content=text,
            usage_metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=ai)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return asyncio.run(self._agenerate(messages, stop=stop, **kwargs))
