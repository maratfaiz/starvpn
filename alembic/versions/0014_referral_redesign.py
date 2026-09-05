"""referral redesign — first_payment_at column + referral_credits ledger

Revision ID: 0014_referral_redesign
Revises: 0013_device_custom_name
Create Date: 2026-09-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_referral_redesign"
down_revision = "0013_device_custom_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("first_payment_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "referral_credits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("referrer_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_referral_credits_referrer_id", "referral_credits", ["referrer_id"])
    op.create_index("ix_referral_credits_created_at", "referral_credits", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_referral_credits_created_at", table_name="referral_credits")
    op.drop_index("ix_referral_credits_referrer_id", table_name="referral_credits")
    op.drop_table("referral_credits")
    op.drop_column("users", "first_payment_at")
