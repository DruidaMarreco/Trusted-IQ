"""Application settings loaded from environment variables."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration read from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Runtime ---
    env: str = Field(default="dev", description="Runtime environment: dev | staging | prod")
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Provider selection ---
    llm_provider: str = "azure_openai"  # azure_openai | openai | anthropic | claude_code | ollama
    # Orchestrator model — selected by the model evaluation (results/model_eval.*):
    # Claude Opus 4.8 ranked #1 (composite 0.955; 100% intent accuracy, top
    # groundedness). Pair with LLM_PROVIDER=claude_code (dev/test, subscription
    # quota) or anthropic. Haiku is the cost-sensitive fallback (composite 0.932).
    # For Azure OpenAI production, re-run `evaluate_models.py --backend providers`
    # to compare GPT deployments and pin the winner here.
    llm_model: str = "claude-opus-4-8"

    # --- Model proxy (optional, OpenAI-compatible gateway / LiteLLM) ---
    # When llm_proxy_base_url is set, ALL models are routed through this single
    # endpoint via the OpenAI-compatible API, overriding the per-provider config
    # below. This is what the metrics benchmark uses to compare models (GPT,
    # Claude, Gemini, ...) behind one gateway and pick the best one.
    llm_proxy_base_url: str = Field(
        default="", description="OpenAI-compatible proxy base URL, e.g. https://gateway.internal/v1"
    )
    llm_proxy_api_key: SecretStr = SecretStr("")

    # --- Azure OpenAI ---
    azure_openai_api_key: SecretStr = SecretStr("")
    azure_openai_endpoint: str = ""  # https://<resource>.openai.azure.com/
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = "gpt-4o"

    # --- OpenAI direct ---
    openai_api_key: SecretStr = SecretStr("")

    # --- Anthropic ---
    anthropic_api_key: SecretStr = SecretStr("")

    # --- Per-agent model overrides (optional) ---
    orchestrator_model: str = Field(default="", description="Override LLM model for orchestrator")
    subagent_a_model: str = Field(default="", description="Override LLM model for subagent A")
    subagent_b_model: str = Field(default="", description="Override LLM model for subagent B")

    # --- FastAPI ---
    app_title: str = "trade-iq-pod"
    app_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
