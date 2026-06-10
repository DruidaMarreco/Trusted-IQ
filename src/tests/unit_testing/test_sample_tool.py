"""Unit tests for the sample tool."""

from app.tools.sample_tool import sample_tool


def test_sample_tool_returns_string() -> None:
    result = sample_tool.invoke({"query": "hello"})
    assert isinstance(result, str)
    assert "hello" in result
