"""Initial SQLite schema scaffold.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-21
"""

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """M0 scaffold only. DB_GO requires M1-002 to convert ARCHITECTURE section 24.2 DDL into Alembic ops."""


def downgrade() -> None:
    """M0 scaffold only. M1-002 drops tables in reverse dependency order."""
