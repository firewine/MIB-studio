from __future__ import annotations

from typing import Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, SecretStr


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


CredentialProvider = Literal["openai", "openai_compatible"]


class CredentialUpsert(StrictModel):
    base_url: AnyUrl
    api_key: SecretStr = Field(min_length=1)
    expires_at: str | None = None


class CredentialRead(StrictModel):
    id: str
    provider: CredentialProvider
    base_url_origin: str
    keychain_ref: str
    is_revoked: bool
    expires_at: str | None = None
    created_at: str
    last_used_at: str | None = None


class CredentialPage(StrictModel):
    items: list[CredentialRead]
