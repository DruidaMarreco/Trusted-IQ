"""Unit tests for the LLM factory: native provider selection vs proxy routing."""

from unittest.mock import MagicMock, patch

from app.config import Settings


@patch("app.llm_factory.init_chat_model")
def test_native_provider_used_without_proxy(mock_init: MagicMock) -> None:
    """With no proxy configured, build_llm uses the selected native provider."""
    from app.llm_factory import build_llm

    cfg = Settings(llm_provider="openai", llm_model="gpt-4o", llm_proxy_base_url="")
    build_llm(cfg=cfg)

    args, kwargs = mock_init.call_args
    assert args[0] == "gpt-4o"
    assert kwargs["model_provider"] == "openai"
    assert "base_url" not in kwargs


@patch("app.llm_factory.init_chat_model")
def test_proxy_routes_all_models_openai_compatible(mock_init: MagicMock) -> None:
    """When a proxy is set, every model is routed through it via the OpenAI API,
    regardless of the requested provider."""
    from app.llm_factory import build_llm

    cfg = Settings(
        llm_provider="anthropic",
        llm_proxy_base_url="https://gateway.example/v1",
    )
    build_llm(model="claude-sonnet-4-6", cfg=cfg)

    args, kwargs = mock_init.call_args
    assert args[0] == "claude-sonnet-4-6"
    assert kwargs["model_provider"] == "openai"
    assert kwargs["base_url"] == "https://gateway.example/v1"
