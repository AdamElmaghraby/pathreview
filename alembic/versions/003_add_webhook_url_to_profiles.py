"""Add webhook_url column to profiles table.

Revision ID: 003
Revises: 002
Create Date: 2026-08-02 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "webhook_url")
