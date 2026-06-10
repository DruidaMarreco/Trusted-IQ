"""Unit tests for the Claude Code chat-model adapter (no real quota is used)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.claude_code_llm import ChatClaudeCode, _parse_query_messages


def test_parse_result_message_text_and_usage() -> None:
    msgs = [
        SimpleNamespace(content=[SimpleNamespace(text="partial")]),
        SimpleNamespace(result="final answer", usage={"input_tokens": 12, "output_tokens": 7}),
    ]
    text, inp, out = _parse_query_messages(msgs)
    assert text == "final answer"
    assert (inp, out) == (12, 7)


def test_parse_falls_back_to_text_blocks_without_result() -> None:
    msgs = [SimpleNamespace(content=[SimpleNamespace(text="hello")])]
    text, inp, out = _parse_query_messages(msgs)
    assert text == "hello"
    assert (inp, out) == (0, 0)


def test_build_llm_returns_claude_code_model() -> None:
    from app.config import Settings
    from app.llm_factory import build_llm

    cfg = Settings(llm_proxy_base_url="")  # ensure proxy path is off
    llm = build_llm(model="opus", provider="claude_code", cfg=cfg)
    assert isinstance(llm, ChatClaudeCode)
    assert llm.model == "opus"


@pytest.mark.asyncio
async def test_agenerate_wraps_sdk_response() -> None:
    async def fake_query(prompt: str, options: object) -> AsyncIterator[object]:
        yield SimpleNamespace(result="DATA_QUERY", usage={"input_tokens": 5, "output_tokens": 2})

    model = ChatClaudeCode(model="haiku")
    with (
        patch("claude_agent_sdk.query", fake_query),
        patch("claude_agent_sdk.ClaudeAgentOptions", lambda **k: object()),
    ):
        result = await model._agenerate([HumanMessage(content="classify this")])

    msg = result.generations[0].message
    assert isinstance(msg, AIMessage)
    assert msg.content == "DATA_QUERY"
    assert msg.usage_metadata is not None
    assert msg.usage_metadata["input_tokens"] == 5
    assert msg.usage_metadata["output_tokens"] == 2
