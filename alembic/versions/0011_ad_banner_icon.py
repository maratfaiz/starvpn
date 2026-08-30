"""ad_banner.icon — pick from a fixed set of icons in the admin editor

Revision ID: 0011_ad_banner_icon
Revises: 0010_admin_accounts_and_ad_banner
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_ad_banner_icon"
down_revision = "0010_admin_accounts_and_ad_banner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ad_banner",
        sa.Column("icon", sa.String(24), nullable=False, server_default="sparkle"),
    )


def downgrade() -> None:
    op.drop_column("ad_banner", "icon")
