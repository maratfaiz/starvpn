"""admin_accounts + admin_sessions (per-account login, invite-key ranks)
   + ad_banner (editable top banner)

Revision ID: 0010_admin_accounts_and_ad_banner
Revises: 0009_drop_magic_link_tokens
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_admin_accounts_and_ad_banner"
down_revision = "0009_drop_magic_link_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rank", sa.String(16), nullable=False),
        sa.Column("invite_key", sa.String(32), nullable=True),
        sa.Column("invited_by_id", sa.BigInteger(), sa.ForeignKey("admin_accounts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_accounts_username", "admin_accounts", ["username"], unique=True)
    op.create_index("ix_admin_accounts_invite_key", "admin_accounts", ["invite_key"], unique=True)

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "admin_id", sa.BigInteger(),
            sa.ForeignKey("admin_accounts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("rank", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_sessions_token_hash", "admin_sessions", ["token_hash"], unique=True)
    op.create_index("ix_admin_sessions_admin_id", "admin_sessions", ["admin_id"])

    op.create_table(
        "ad_banner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("text", sa.String(300), nullable=False, server_default=""),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("link_label", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ad_banner")
    op.drop_index("ix_admin_sessions_admin_id", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_token_hash", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_index("ix_admin_accounts_invite_key", table_name="admin_accounts")
    op.drop_index("ix_admin_accounts_username", table_name="admin_accounts")
    op.drop_table("admin_accounts")
