from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import json


class Settings(BaseSettings):
    app_name: str = "ChatbotMCP"
    app_env: str = "development"
    debug: bool = False

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # LLM
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    default_llm_provider: str = "groq"
    default_model: str = "llama-3.3-70b-versatile"

    # Groq (free, fast, open-source models via API — console.groq.com)
    groq_api_key: str = Field(default="", env="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")

    # Ollama (local open-source LLM)
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", env="OLLAMA_MODEL")

    # MCP Servers
    gmail_mcp_url: str = Field(default="http://gmail-mcp:8001", env="GMAIL_MCP_URL")

    # CORS
    cors_origins: str = Field(
        default='["http://localhost:3000"]',
        env="CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        try:
            return json.loads(self.cors_origins)
        except Exception:
            return ["http://localhost:3000"]

    # Rate limiting
    rate_limit_per_minute: int = 60
    max_tool_calls_per_turn: int = 10
    max_conversation_length: int = 100

    log_level: str = "INFO"
    backend_port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
