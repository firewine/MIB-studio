from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from services.api.app.core.config import Settings
from services.api.app.main import create_app
from services.shared.db.models import AuditEvent, Credential
from services.shared.db.session import create_sqlite_engine, session_factory
from services.shared.security.credential_store import CredentialStoreUnavailable, credential_account, credential_keychain_ref


class FakeCredentialStore:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.secrets: dict[str, str] = {}
        self.set_calls: list[tuple[str, str]] = []
        self.deleted: list[str] = []

    def set_secret(self, account: str, secret: str) -> None:
        if not self.available:
            raise CredentialStoreUnavailable("fake keychain unavailable")
        self.secrets[account] = secret
        self.set_calls.append((account, secret))

    def delete_secret(self, account: str) -> None:
        if not self.available:
            raise CredentialStoreUnavailable("fake keychain unavailable")
        self.deleted.append(account)
        self.secrets.pop(account, None)


def alembic_config(db_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def prepare_database(tmp_path: Path) -> str:
    db_path = tmp_path / "credentials.db"
    command.upgrade(alembic_config(db_path), "head")
    return f"sqlite:///{db_path}"


def auth_headers(token: str = "test-token") -> dict[str, str]:
    return {"host": "127.0.0.1:8910", "authorization": f"Bearer {token}"}


def client_for(database_url: str, store: FakeCredentialStore) -> httpx.AsyncClient:
    settings = Settings(app_env="production", dev_auth="bootstrap", bootstrap_token="test-token", database_url=database_url)
    app = create_app(settings)
    app.state.credential_store = store
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8910",
    )


async def call_api(awaitable: object) -> httpx.Response:
    return await asyncio.wait_for(awaitable, timeout=10)


@pytest.mark.asyncio
async def test_key_saved_to_keyring_and_never_returned_or_stored_plaintext(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    store = FakeCredentialStore()
    secret = "fake-credential-value"
    expected_account = credential_account("openai", "https://api.openai.com/v1")

    async with client_for(database_url, store) as client:
        upserted = await call_api(
            client.put(
                "/credentials/openai",
                json={"base_url": "https://api.openai.com/v1", "api_key": secret},
                headers=auth_headers(),
            )
        )
        listed = await call_api(client.get("/credentials", headers=auth_headers()))
        deleted = await call_api(client.delete("/credentials/openai", headers=auth_headers()))
        listed_after_delete = await call_api(client.get("/credentials", headers=auth_headers()))

    assert upserted.status_code == 204
    assert upserted.content == b""
    assert store.set_calls == [(expected_account, secret)]
    assert store.secrets == {}
    assert store.deleted == [expected_account]
    assert deleted.status_code == 204

    body = listed.json()
    assert secret not in listed.text
    assert body["items"][0]["provider"] == "openai"
    assert body["items"][0]["base_url_origin"] == "https://api.openai.com"
    assert body["items"][0]["keychain_ref"] == credential_keychain_ref(expected_account)
    assert body["items"][0]["is_revoked"] is False
    assert listed_after_delete.json()["items"][0]["is_revoked"] is True

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            credential = session.query(Credential).one()
            assert credential.provider == "openai"
            assert credential.base_url == "https://api.openai.com/v1"
            assert credential.keychain_ref == credential_keychain_ref(expected_account)
            assert credential.is_revoked == 1
            raw_credential = json.dumps([dict(row) for row in session.execute(text("SELECT * FROM credential")).mappings()], default=str)
            raw_audit = json.dumps([dict(row) for row in session.execute(text("SELECT * FROM audit_event")).mappings()], default=str)
            assert secret not in raw_credential
            assert secret not in raw_audit
            events = session.query(AuditEvent).all()
            assert sorted(event.action for event in events) == ["deleted", "set"]
            assert all(event.event_type == "credential_access" for event in events)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_keychain_unavailable_returns_503_without_db_write(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    store = FakeCredentialStore(available=False)

    async with client_for(database_url, store) as client:
        response = await call_api(
            client.put(
                "/credentials/openai",
                json={"base_url": "https://api.openai.com/v1", "api_key": "fake-unavailable"},
                headers=auth_headers(),
            )
        )

    assert response.status_code == 503
    assert response.json()["error_code"] == "KEYCHAIN_UNAVAILABLE"
    assert response.json()["details"]["provider"] == "openai"

    engine = create_sqlite_engine(database_url)
    factory = session_factory(engine)
    try:
        with factory() as session:
            assert session.query(Credential).count() == 0
            assert session.query(AuditEvent).count() == 0
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_provider_and_base_url_validation(tmp_path: Path) -> None:
    database_url = prepare_database(tmp_path)
    store = FakeCredentialStore()

    async with client_for(database_url, store) as client:
        invalid_provider = await call_api(
            client.put(
                "/credentials/anthropic",
                json={"base_url": "https://api.anthropic.com/v1", "api_key": "fake-wrong-provider"},
                headers=auth_headers(),
            )
        )
        wrong_openai_host = await call_api(
            client.put(
                "/credentials/openai",
                json={"base_url": "https://example.com/v1", "api_key": "fake-wrong-host"},
                headers=auth_headers(),
            )
        )
        insecure_remote = await call_api(
            client.put(
                "/credentials/openai_compatible",
                json={"base_url": "http://remote.example/v1", "api_key": "fake-insecure"},
                headers=auth_headers(),
            )
        )

    assert invalid_provider.status_code == 422
    assert invalid_provider.json()["details"]["field"] == "provider"
    assert wrong_openai_host.status_code == 422
    assert wrong_openai_host.json()["details"]["field"] == "base_url"
    assert insecure_remote.status_code == 422
    assert insecure_remote.json()["details"]["field"] == "base_url"
    assert store.secrets == {}
