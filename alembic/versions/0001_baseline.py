"""baseline — reflects schema as it existed before Alembic was introduced

This migration exists so the migration history has a starting point. It is
NOT meant to be run with `alembic upgrade` against an already-deployed
database — those already have these 5 tables (created via
`Base.metadata.create_all` at bot startup). On an existing deployment, run:

    alembic stamp 0001_baseline

to mark the DB as being at this revision without re-executing the CREATEs.
On a brand-new empty database, `alembic upgrade head` will create
everything from scratch (create_all also still runs at bot startup and is
idempotent, so this is redundant-but-harmless for fresh installs too).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(256), nullable=True),
        sa.Column("marzban_username", sa.String(128), nullable=True, unique=True),
        sa.Column("referrer_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=True),
        sa.Column("referral_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_days_granted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_stars_paid", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("referral_bonus_counted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("subscription_expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_referrer_id", "users", ["referrer_id"])

    op.create_table(
        "devices",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("marzban_username", sa.String(128), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_devices_telegram_id", "devices", ["telegram_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.String(255), nullable=False, unique=True),
        sa.Column("telegram_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(16), nullable=False, server_default="stars"),
        sa.Column("asset", sa.String(16), nullable=True),
        sa.Column("invoice_id", sa.BigInteger(), nullable=True),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_telegram_id", "payments", ["telegram_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])

    op.create_table(
        "guest_orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("plan_key", sa.String(16), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("marzban_username", sa.String(128), nullable=True, unique=True),
        sa.Column("vless_link", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_guest_orders_public_id", "guest_orders", ["public_id"])
    op.create_index("ix_guest_orders_status", "guest_orders", ["status"])

    op.create_table(
        "gift_notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "recipient_id", sa.BigInteger(),
            sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("sender_name", sa.String(128), nullable=False),
        sa.Column("plan_label", sa.String(64), nullable=False),
        sa.Column("plan_days", sa.Integer(), nullable=False),
        sa.Column("seen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_gift_notifications_recipient_id", "gift_notifications", ["recipient_id"])


def downgrade() -> None:
    op.drop_table("gift_notifications")
    op.drop_table("guest_orders")
    op.drop_table("payments")
    op.drop_table("devices")
    op.drop_table("users")
