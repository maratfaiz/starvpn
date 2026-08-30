"""drop unused magic_link_tokens table

Magic-link auth was replaced by email+password+verification-code in
0008_password_auth — the table and model are no longer referenced anywhere.

Revision ID: 0009_drop_magic_link_tokens
Revises: 0008_password_auth
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_drop_magic_link_tokens"
down_revision = "0008_password_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("magic_link_tokens")


def downgrade() -> None:
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
