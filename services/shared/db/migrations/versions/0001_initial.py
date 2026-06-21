"""Initial SQLite schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op

from services.shared.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    failures = list(bind.exec_driver_sql("PRAGMA foreign_key_check"))
    if failures:
        raise RuntimeError(f"foreign key check failed after initial migration: {failures}")


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
