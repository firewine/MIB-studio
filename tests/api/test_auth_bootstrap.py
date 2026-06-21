from __future__ import annotations

import json

import httpx
import pytest
from pydantic import ValidationError

from services.api.app.core.config import Settings
from services.api.app.main import create_app, create_bootstrap_line
from services.shared.security.auth import format_bootstrap_line


def client_for(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(settings)),
        base_url="http://127.0.0.1:8910",
    )


def allowed_headers(token: str | None = None, origin: str | None = None) -> dict[str, str]:
    headers = {"host": "127.0.0.1:8910"}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    if origin is not None:
        headers["origin"] = origin
    return headers


@pytest.mark.asyncio
async def test_healthz_is_unauthenticated_and_sets_trace_id() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get("/healthz", headers=allowed_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.0.0-day0"}
    assert response.headers["x-trace-id"]


@pytest.mark.asyncio
async def test_missing_token_rejected_for_non_healthz() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get("/projects", headers=allowed_headers())

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_invalid_token_rejected() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get("/projects", headers=allowed_headers("wrong-token"))

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_INVALID"


@pytest.mark.asyncio
async def test_valid_token_reaches_locked_future_stub() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get("/model-catalog", headers=allowed_headers("test-token"))

    body = response.json()
    assert response.status_code == 409
    assert body["error_code"] == "MILESTONE_LOCKED"
    assert body["details"]["operation_id"] == "getModelCatalog"
    assert body["details"]["current_milestone"] == "M1-001"


@pytest.mark.asyncio
async def test_host_not_local_rejected_before_auth() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get(
            "/projects",
            headers={"host": "evil.example", "authorization": "Bearer test-token"},
        )

    assert response.status_code == 403
    assert response.json()["error_code"] == "HOST_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_origin_not_allowlisted_rejected_before_auth() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.get(
            "/projects",
            headers=allowed_headers("test-token", origin="https://evil.example"),
        )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ORIGIN_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_cors_preflight_allowlist_bypasses_bearer_after_host_origin_validation() -> None:
    settings = Settings(app_env="development", dev_auth="bootstrap", bootstrap_token="test-token")
    async with client_for(settings) as client:
        response = await client.options(
            "/projects",
            headers={
                "host": "127.0.0.1:8910",
                "origin": "tauri://localhost",
                "access-control-request-method": "GET",
                "access-control-request-headers": "Authorization, Content-Type",
            },
        )

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["access-control-allow-origin"] == "tauri://localhost"
    assert "authorization" in response.headers["access-control-allow-headers"]


@pytest.mark.asyncio
async def test_request_body_size_limit_runs_before_handler() -> None:
    settings = Settings(
        app_env="production",
        dev_auth="bootstrap",
        bootstrap_token="test-token",
        body_max_bytes=4,
    )
    async with client_for(settings) as client:
        response = await client.post(
            "/projects",
            content=b"too-large",
            headers=allowed_headers("test-token"),
        )

    assert response.status_code == 413
    assert response.json()["error_code"] == "REQUEST_TOO_LARGE"


@pytest.mark.asyncio
async def test_token_file_mode_is_development_only_and_accepts_file_token(tmp_path) -> None:  # type: ignore[no-untyped-def]
    token_file = tmp_path / ".mib-dev-token"
    token_file.write_text("file-token\n", encoding="utf-8")
    settings = Settings(app_env="development", dev_auth="token_file", token_file_path=token_file)

    async with client_for(settings) as client:
        response = await client.get("/model-catalog", headers=allowed_headers("file-token"))

    assert response.status_code == 409
    assert response.json()["error_code"] == "MILESTONE_LOCKED"


def test_dev_bypass_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", dev_auth="bypass")


def test_bootstrap_line_format_contains_exactly_one_marker() -> None:
    line = format_bootstrap_line("http://127.0.0.1:1234", "secret-token", pid=42)

    assert line.count("MIB_BOOTSTRAP ") == 1
    payload = json.loads(line.removeprefix("MIB_BOOTSTRAP "))
    assert payload == {"base_url": "http://127.0.0.1:1234", "pid": 42, "token": "secret-token"}


def test_create_bootstrap_line_uses_settings_token() -> None:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token")

    line = create_bootstrap_line(settings, port=9876, pid=99)

    payload = json.loads(line.removeprefix("MIB_BOOTSTRAP "))
    assert payload["base_url"] == "http://127.0.0.1:9876"
    assert payload["token"] == "test-token"
    assert payload["pid"] == 99
