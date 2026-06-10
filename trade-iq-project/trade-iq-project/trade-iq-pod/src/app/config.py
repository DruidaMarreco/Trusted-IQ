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
    llm_provider: str = "azure_openai"  # azure_openai | openai | anthropic | ollama
    llm_model: str = "gpt-4o"

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
