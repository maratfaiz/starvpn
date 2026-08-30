"""users — password_hash + email_verified; new email_verification_codes table

Веб-аккаунт переходит с magic-link на обычный вход email+пароль,
с подтверждением почты одноразовым кодом при регистрации.

Revision ID: 0008_password_auth
Revises: 0007_gift_payments
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_password_auth"
down_revision = "0007_gift_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_email_verification_codes_email", "email_verification_codes", ["email"]
    )


def downgrade() -> None:
    op.drop_index("ix_email_verification_codes_email", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "password_hash")
