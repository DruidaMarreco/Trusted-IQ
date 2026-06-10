"""Shared pytest fixtures for unit tests."""

from collections.abc import Callable
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models import BaseChatModel


@pytest.fixture
def make_llm() -> Callable[..., BaseChatModel]:
    """Factory for a fake chat model whose ``ainvoke`` returns the given message
    contents in order (one per orchestration step). No network, no real LLM."""

    def _factory(*contents: str) -> BaseChatModel:
        llm = AsyncMock(spec=BaseChatModel)
        llm.ainvoke = AsyncMock(side_effect=[SimpleNamespace(content=c) for c in contents])
        return cast(BaseChatModel, llm)

    return _factory
