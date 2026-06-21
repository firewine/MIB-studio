from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from services.shared.db.models.base import Base


class SchemaMigration(Base):
    __tablename__ = "schema_migration"

    version: Mapped[str] = mapped_column(Text, primary_key=True)
    applied_at: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
