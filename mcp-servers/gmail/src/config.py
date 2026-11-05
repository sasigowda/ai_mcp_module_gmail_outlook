from pydantic_settings import BaseSettings
from pydantic import Field


class GmailMCPSettings(BaseSettings):
    app_name: str = "Gmail MCP Server"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8001/oauth/gmail/callback",
        env="GOOGLE_REDIRECT_URI"
    )

    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/1", env="REDIS_URL")

    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    secret_key: str = Field(..., env="SECRET_KEY")

    gmail_scopes: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    token_dir: str = "/app/tokens"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = GmailMCPSettings()
