"""payments — gift columns for website gift flow (card/ЮMoney)

Revision ID: 0007_gift_payments
Revises: 0006_app_settings
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_gift_payments"
down_revision = "0006_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("is_gift", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("payments", sa.Column("gift_sender_id", sa.BigInteger(), nullable=True))
    op.add_column("payments", sa.Column("gift_anon", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("payments", sa.Column("gift_message", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "gift_message")
    op.drop_column("payments", "gift_anon")
    op.drop_column("payments", "gift_sender_id")
    op.drop_column("payments", "is_gift")
