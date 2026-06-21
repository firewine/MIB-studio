from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.errors import APIError
from services.api.app.schemas.credential import CredentialPage, CredentialProvider, CredentialRead, CredentialUpsert
from services.shared.db.models import AuditEvent, Credential
from services.shared.security.credential_store import (
    CredentialStoreUnavailable,
    credential_account,
    credential_keychain_ref,
    normalize_credential_base_url,
)


class SecretStore(Protocol):
    def set_secret(self, account: str, secret: str) -> None:
        ...

    def delete_secret(self, account: str) -> None:
        ...


def new_id() -> str:
    return uuid.uuid4().hex


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class CredentialService:
    def __init__(self, session: Session, secret_store: SecretStore) -> None:
        self.session = session
        self.secret_store = secret_store

    def list_credentials(self) -> CredentialPage:
        credentials = list(self.session.scalars(select(Credential).order_by(Credential.provider.asc())))
        return CredentialPage(items=[self._read_credential(item) for item in credentials])

    def upsert_credential(self, provider: str, payload: CredentialUpsert) -> None:
        validated_provider = self._provider_or_422(provider)
        try:
            normalized = normalize_credential_base_url(validated_provider, str(payload.base_url))
        except ValueError as exc:
            raise APIError(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status_code=422,
                details={"field": "base_url", "reason": str(exc)},
            ) from exc

        account = credential_account(validated_provider, normalized.value)
        keychain_ref = credential_keychain_ref(account)
        try:
            self.secret_store.set_secret(account, payload.api_key.get_secret_value())
        except CredentialStoreUnavailable as exc:
            raise APIError(
                "KEYCHAIN_UNAVAILABLE",
                "OS keychain is unavailable.",
                status_code=503,
                details={"provider": validated_provider, "platform": exc.platform},
            ) from exc

        now = utc_now()
        credential = self.session.scalar(select(Credential).where(Credential.provider == validated_provider))
        if credential is None:
            credential = Credential(
                id=new_id(),
                provider=validated_provider,
                base_url=normalized.value,
                keychain_ref=keychain_ref,
                is_revoked=0,
                expires_at=payload.expires_at,
                created_at=now,
            )
            self.session.add(credential)
        else:
            credential.base_url = normalized.value
            credential.keychain_ref = keychain_ref
            credential.is_revoked = 0
            credential.revoked_at = None
            credential.expires_at = payload.expires_at
        self.session.flush()
        self._audit(
            action="set",
            credential=credential,
            details={
                "provider": credential.provider,
                "base_url_origin": normalized.origin,
                "keychain_ref": credential.keychain_ref,
            },
            ts=now,
        )

    def delete_credential(self, provider: str) -> None:
        validated_provider = self._provider_or_422(provider)
        credential = self.session.scalar(select(Credential).where(Credential.provider == validated_provider))
        if credential is None:
            return

        account = credential_account(credential.provider, credential.base_url)
        try:
            self.secret_store.delete_secret(account)
        except CredentialStoreUnavailable as exc:
            raise APIError(
                "KEYCHAIN_UNAVAILABLE",
                "OS keychain is unavailable.",
                status_code=503,
                details={"provider": validated_provider, "platform": exc.platform},
            ) from exc

        now = utc_now()
        credential.is_revoked = 1
        credential.revoked_at = now
        self.session.flush()
        self._audit(
            action="deleted",
            credential=credential,
            details={
                "provider": credential.provider,
                "base_url_origin": _origin_for(credential.base_url),
                "keychain_ref": credential.keychain_ref,
            },
            ts=now,
        )

    def _provider_or_422(self, provider: str) -> CredentialProvider:
        if provider not in {"openai", "openai_compatible"}:
            raise APIError(
                "VALIDATION_ERROR",
                "Request validation failed.",
                status_code=422,
                details={"field": "provider", "reason": "unsupported credential provider"},
            )
        return provider  # type: ignore[return-value]

    def _read_credential(self, credential: Credential) -> CredentialRead:
        return CredentialRead(
            id=credential.id,
            provider=credential.provider,  # type: ignore[arg-type]
            base_url_origin=_origin_for(credential.base_url),
            keychain_ref=credential.keychain_ref,
            is_revoked=bool(credential.is_revoked),
            expires_at=credential.expires_at,
            created_at=credential.created_at,
            last_used_at=credential.last_used_at,
        )

    def _audit(self, *, action: str, credential: Credential, details: dict[str, str], ts: str) -> None:
        self.session.add(
            AuditEvent(
                id=new_id(),
                ts=ts,
                event_type="credential_access",
                resource_type="credential",
                resource_id=credential.id,
                action=action,
                policy_version="security.v0.3",
                details_json=json.dumps(details, sort_keys=True, separators=(",", ":")),
                trace_id=None,
                retention_until=(datetime.now(UTC) + timedelta(days=365)).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                created_at=ts,
            )
        )
        self.session.flush()


def _origin_for(base_url: str) -> str:
    parts = urlsplit(base_url)
    if parts.port is None or (parts.scheme == "https" and parts.port == 443) or (parts.scheme == "http" and parts.port == 80):
        netloc = parts.hostname or parts.netloc
    else:
        host = parts.hostname or parts.netloc
        netloc = f"[{host}]" if ":" in host and not host.startswith("[") else host
        netloc = f"{netloc}:{parts.port}"
    return f"{parts.scheme}://{netloc}"
