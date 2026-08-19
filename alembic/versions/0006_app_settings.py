"""app_settings — key-value store, currently used for payment provider toggles

Revision ID: 0006_app_settings
Revises: 0005_wiki_articles
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_app_settings"
down_revision = "0005_wiki_articles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(500), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
