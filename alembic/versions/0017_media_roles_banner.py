"""media_files, admin_roles (+ admin_accounts.role_id и др.), баннер, картинки блоков бота

Revision ID: 0017_media_roles_banner
Revises: 0016_fix_referral_count
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_media_roles_banner"
down_revision = "0016_fix_referral_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_files",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(200), nullable=False, server_default=""),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("tg_file_id", sa.String(255), nullable=True),
        sa.Column("uploaded_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "admin_roles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.String(200), nullable=False, server_default=""),
        sa.Column("sections", sa.String(300), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.add_column("admin_accounts", sa.Column("role_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_admin_accounts_role_id", "admin_accounts", "admin_roles", ["role_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_admin_accounts_role_id", "admin_accounts", ["role_id"])
    op.add_column("admin_accounts", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("admin_accounts", sa.Column("display_name", sa.String(64), nullable=False, server_default=""))
    op.add_column("admin_accounts", sa.Column("last_login_at", sa.DateTime(), nullable=True))

    op.add_column("ad_banner", sa.Column("icon_media_id", sa.BigInteger(), nullable=True))
    op.add_column("ad_banner", sa.Column("style", sa.String(16), nullable=False, server_default="gold"))
    op.add_column("ad_banner", sa.Column("starts_at", sa.DateTime(), nullable=True))
    op.add_column("ad_banner", sa.Column("ends_at", sa.DateTime(), nullable=True))
    op.add_column("ad_banner", sa.Column("show_countdown", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("ad_banner", sa.Column("dismissible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("ad_banner", sa.Column("views", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("ad_banner", sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"))

    op.add_column("bot_blocks", sa.Column("image", sa.String(500), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("bot_blocks", "image")
    for col in ("clicks", "views", "dismissible", "show_countdown", "ends_at", "starts_at", "style", "icon_media_id"):
        op.drop_column("ad_banner", col)
    for col in ("last_login_at", "display_name", "is_active"):
        op.drop_column("admin_accounts", col)
    op.drop_index("ix_admin_accounts_role_id", table_name="admin_accounts")
    op.drop_constraint("fk_admin_accounts_role_id", "admin_accounts", type_="foreignkey")
    op.drop_column("admin_accounts", "role_id")
    op.drop_table("admin_roles")
    op.drop_table("media_files")
