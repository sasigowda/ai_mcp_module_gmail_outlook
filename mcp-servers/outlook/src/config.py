from pydantic_settings import BaseSettings
from pydantic import Field


class OutlookMCPSettings(BaseSettings):
    app_name: str = "Outlook MCP Server"
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False

    azure_client_id: str = Field(..., env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., env="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(default="common", env="AZURE_TENANT_ID")
    azure_redirect_uri: str = Field(
        default="http://localhost:8002/oauth/outlook/callback",
        env="AZURE_REDIRECT_URI"
    )

    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/2", env="REDIS_URL")

    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    secret_key: str = Field(..., env="SECRET_KEY")

    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    outlook_scopes: list[str] = [
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/User.Read",
        "offline_access",
    ]

    token_dir: str = "/app/tokens"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = OutlookMCPSettings()
