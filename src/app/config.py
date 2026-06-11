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
    # azure = Azure AI Foundry (OpenAI-compatible /openai/v1, call by deployment name)
    # azure_openai = classic Azure OpenAI (deployment-based); also: openai | anthropic | claude_code | ollama
    llm_provider: str = "azure_openai"
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

    # --- Google Gemini (not served via Azure Foundry) ---
    google_api_key: SecretStr = SecretStr("")

    # --- Copilot proxy (local Anthropic-style gateway: /v1/messages, x-api-key) ---
    # e.g. a LiteLLM/copilot proxy on localhost:4000 that fronts many models.
    copilot_proxy_base_url: str = "http://localhost:4000"
    copilot_proxy_api_key: SecretStr = SecretStr("sk-dummy")

    # --- Anthropic ---
    anthropic_api_key: SecretStr = SecretStr("")

    # --- TPO tool backends (CDT TextToSQL agent, ERDC Optimizer API) ---
    # When a base URL is set, the orchestrator calls the live service over HTTP;
    # otherwise it falls back to deterministic mock output (dev/test/eval).
    cdt_base_url: str = Field(default="", description="CDT TextToSQL service base URL")
    cdt_api_key: SecretStr = SecretStr("")
    cdt_timeout_s: float = 30.0
    erdc_base_url: str = Field(default="", description="ERDC Optimizer API base URL")
    erdc_api_key: SecretStr = SecretStr("")
    erdc_timeout_s: float = 30.0
    tool_max_retries: int = Field(default=2, ge=0, description="Retries on transient tool HTTP failures")

    # --- Per-agent model overrides (optional) ---
    orchestrator_model: str = Field(default="", description="Override LLM model for orchestrator")
    subagent_a_model: str = Field(default="", description="Override LLM model for subagent A")
    subagent_b_model: str = Field(default="", description="Override LLM model for subagent B")

    # --- FastAPI ---
    app_title: str = "trade-iq-pod"
    app_version: str = "0.1.0"
    debug: bool = False


settings = Settings()
