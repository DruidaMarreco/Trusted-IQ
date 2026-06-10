"""LLM factory — provider-agnostic chat model builder.

Uses LangChain's `init_chat_model` so all agents receive a `BaseChatModel`
regardless of underlying provider (Azure OpenAI, OpenAI, Anthropic, Ollama…).
"""

from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.config import Settings
from app.config import settings as _default_settings


def build_llm(
    model: str | None = None,
    provider: str | None = None,
    cfg: Settings | None = None,
    **kwargs: object,
) -> BaseChatModel:
    """Return a configured chat model for any supported provider.

    Args:
        model: Model name override. Falls back to ``cfg.llm_model``.
        provider: Provider override. Falls back to ``cfg.llm_provider``.
        cfg: Settings instance. Defaults to the module-level singleton.
        **kwargs: Extra kwargs forwarded to ``init_chat_model``.

    Returns:
        A ``BaseChatModel`` instance ready for ``.invoke`` / ``.ainvoke``.
    """
    cfg = cfg or _default_settings
    resolved_model = model or cfg.llm_model
    resolved_provider = provider or cfg.llm_provider

    provider_kwargs: dict[str, Any] = {}

    if resolved_provider == "azure_openai":
        provider_kwargs = {
            "azure_endpoint": cfg.azure_openai_endpoint,
            "api_key": cfg.azure_openai_api_key,
            "api_version": cfg.azure_openai_api_version,
            "azure_deployment": cfg.azure_openai_deployment,
        }
    elif resolved_provider == "openai":
        provider_kwargs = {"api_key": cfg.openai_api_key}
    elif resolved_provider == "anthropic":
        provider_kwargs = {"api_key": cfg.anthropic_api_key}
    # ollama / others: no auth needed, init_chat_model handles defaults

    return init_chat_model(  # type: ignore[no-any-return]
        resolved_model,
        model_provider=resolved_provider,
        **provider_kwargs,
        **kwargs,
    )
