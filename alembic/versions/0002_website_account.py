"""website account — email/is_admin on users, magic links, web sessions, support tickets

Revision ID: 0002_website_account
Revises: 0001_baseline
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_website_account"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_magic_link_tokens_email", "magic_link_tokens", ["email"])
    op.create_index("ix_magic_link_tokens_token_hash", "magic_link_tokens", ["token_hash"])

    op.create_table(
        "web_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.BigInteger(),
            sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_web_sessions_token_hash", "web_sessions", ["token_hash"])
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.BigInteger(),
            sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("message", sa.String(4000), nullable=False),
        sa.Column("platform", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("admin_reply", sa.String(4000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])


def downgrade() -> None:
    op.drop_table("support_tickets")
    op.drop_table("web_sessions")
    op.drop_table("magic_link_tokens")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "email")
