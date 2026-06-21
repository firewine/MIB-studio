from __future__ import annotations

import json
import os
import secrets
from typing import Protocol


class AuthSettings(Protocol):
    app_env: str
    bind_host: str
    dev_auth: str
    bootstrap_token: str
    token_file_path: object


class SecurityError(Exception):
    def __init__(self, error_code: str, message: str, *, status_code: int = 400) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def generate_bootstrap_token() -> str:
    return secrets.token_urlsafe(32)


def bootstrap_payload(base_url: str, token: str, pid: int | None = None) -> dict[str, object]:
    return {"base_url": base_url, "token": token, "pid": os.getpid() if pid is None else pid}


def format_bootstrap_line(base_url: str, token: str, pid: int | None = None) -> str:
    payload = json.dumps(bootstrap_payload(base_url, token, pid), sort_keys=True, separators=(",", ":"))
    return f"MIB_BOOTSTRAP {payload}"


def auth_is_bypassed(settings: AuthSettings) -> bool:
    return (
        settings.dev_auth == "bypass"
        and settings.app_env == "development"
        and settings.bind_host == "127.0.0.1"
    )


def expected_token(settings: AuthSettings) -> str:
    if settings.dev_auth == "token_file":
        if settings.app_env != "development":
            raise SecurityError("AUTH_MODE_FORBIDDEN", "token_file auth is development-only.", status_code=500)
        token_path = getattr(settings, "token_file_path")
        try:
            token = token_path.read_text(encoding="utf-8").strip()  # type: ignore[attr-defined]
        except FileNotFoundError as exc:
            raise SecurityError("AUTH_TOKEN_UNAVAILABLE", "Development token file is missing.", status_code=500) from exc
        if not token:
            raise SecurityError("AUTH_TOKEN_UNAVAILABLE", "Development token file is empty.", status_code=500)
        return token
    return settings.bootstrap_token


def validate_bearer_header(authorization: str | None, settings: AuthSettings) -> None:
    if auth_is_bypassed(settings):
        return
    if not authorization:
        raise SecurityError("AUTH_REQUIRED", "Bearer token is required.", status_code=401)

    scheme, separator, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not supplied.strip():
        raise SecurityError("AUTH_REQUIRED", "Bearer token is required.", status_code=401)

    expected = expected_token(settings)
    if not secrets.compare_digest(supplied.strip(), expected):
        raise SecurityError("AUTH_INVALID", "Bearer token is invalid.", status_code=401)
