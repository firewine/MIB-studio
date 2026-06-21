from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from services.shared.security.auth import generate_bootstrap_token


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["development", "production", "test"] = Field(
        default="development",
        alias="APP_ENV",
    )
    version: str = Field(default="0.0.0-day0", alias="MIB_VERSION")
    bind_host: str = Field(default="127.0.0.1", alias="MIB_BIND_HOST")
    bind_port: int = Field(default=0, alias="MIB_BIND_PORT")
    dev_auth: Literal["bootstrap", "token_file", "bypass"] = Field(
        default="bootstrap",
        alias="MIB_DEV_AUTH",
    )
    bootstrap_token: str = Field(
        default_factory=generate_bootstrap_token,
        alias="MIB_BOOTSTRAP_TOKEN",
    )
    token_file_path: Path = Field(default=Path(".mib-dev-token"), alias="MIB_TOKEN_FILE")
    body_max_bytes: int = Field(default=1_048_576, alias="MIB_BODY_MAX_BYTES")
    database_url: str = Field(default="sqlite:///mib_studio.db", alias="MIB_DATABASE_URL")

    @model_validator(mode="after")
    def validate_security_mode(self) -> "Settings":
        if self.bind_host != "127.0.0.1":
            raise ValueError("local API must bind to 127.0.0.1")
        if self.app_env == "production" and self.dev_auth != "bootstrap":
            raise ValueError("production accepts only MIB_DEV_AUTH=bootstrap")
        if self.dev_auth in {"token_file", "bypass"} and self.app_env != "development":
            raise ValueError(f"MIB_DEV_AUTH={self.dev_auth} is development-only")
        return self


def load_settings() -> Settings:
    return Settings()
