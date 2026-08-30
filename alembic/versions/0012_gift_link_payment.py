"""payments.gift_link_code / gift_claimed — gift subscriptions by shareable link

Revision ID: 0012_gift_link_payment
Revises: 0011_ad_banner_icon
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_gift_link_payment"
down_revision = "0011_ad_banner_icon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("gift_link_code", sa.String(16), nullable=True),
    )
    op.create_unique_constraint(
        "uq_payments_gift_link_code", "payments", ["gift_link_code"]
    )
    op.create_index(
        "ix_payments_gift_link_code", "payments", ["gift_link_code"]
    )
    op.add_column(
        "payments",
        sa.Column("gift_claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("payments", "gift_claimed")
    op.drop_index("ix_payments_gift_link_code", table_name="payments")
    op.drop_constraint("uq_payments_gift_link_code", "payments", type_="unique")
    op.drop_column("payments", "gift_link_code")
