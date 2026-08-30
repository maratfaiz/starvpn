"""devices.custom_name — user-given device name, editable any time

Revision ID: 0013_device_custom_name
Revises: 0012_gift_link_payment
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_device_custom_name"
down_revision = "0012_gift_link_payment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("custom_name", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("devices", "custom_name")
