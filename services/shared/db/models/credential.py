from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class Credential(Base):
    __tablename__ = "credential"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    keychain_ref: Mapped[str] = mapped_column(Text, nullable=False)
    is_revoked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked_at: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_used_at: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("provider IN ('openai','openai_compatible')", name="credential_provider"),
        CheckConstraint("is_revoked IN (0,1)", name="credential_is_revoked_bool"),
        UniqueConstraint("provider", name="uq_credential_provider"),
    )
