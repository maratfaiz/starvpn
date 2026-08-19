"""users.ban_reason — причина бана, видна забаненному пользователю

Revision ID: 0003_ban_reason
Revises: 0002_website_account
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_ban_reason"
down_revision = "0002_website_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ban_reason", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ban_reason")
