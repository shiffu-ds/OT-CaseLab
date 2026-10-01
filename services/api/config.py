import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    database_url: str = f"sqlite:///{ROOT / '.runtime' / 'otcaselab.db'}"
    app_origin: str = "http://localhost:3005"
    environment: str = "development"
    cookie_secure: bool = False
    allow_demo: bool = True
    session_hours: int = 12
    mcp_service_secret: str = ""
    mcp_transport: str = "stdio"
    mcp_url: str = "http://mcp:9000/mcp"
    mcp_http_bearer_token: str = ""
    provider_mode: str = "scripted"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    redis_url: str = "redis://redis:6379/0"
    job_mode: str = "local"
    nlp_mode: str = "baseline"
    cv_mode: str = "baseline"
    model_cache_path: str = str(ROOT / ".runtime" / "models")
    private_asset_path: str = str(ROOT / ".runtime" / "uploads")
    request_limit_bytes: int = 6 * 1024 * 1024
    research_exports_enabled: bool = False
    research_export_secret: str = ""
    agent_deadline_seconds: int = 60
    agent_max_calls: int = 8
    agent_planner: str = "rule"
    model_cpu_threads: int = 2

    @model_validator(mode="after")
    def security_config(self):
        if self.environment == "production":
            if not self.cookie_secure or not self.app_origin.startswith("https://"):
                raise ValueError("Production requires HTTPS APP_ORIGIN and COOKIE_SECURE=true")
            if len(self.mcp_service_secret) < 32:
                raise ValueError("Set MCP_SERVICE_SECRET to at least 32 random characters")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL DATABASE_URL")
        elif not self.mcp_service_secret:
            directory = ROOT / ".runtime"
            directory.mkdir(exist_ok=True)
            path = directory / "mcp-secret"
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as handle:
                    handle.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
            self.mcp_service_secret = path.read_text().strip()
        return self


@lru_cache
def get_settings():
    return Settings()
