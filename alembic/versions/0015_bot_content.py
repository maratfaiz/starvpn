"""bot_texts + bot_blocks — редактор бота в админке (/admin → Бот)

Revision ID: 0015_bot_content
Revises: 0014_wiki_rich_content
Create Date: 2026-09-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_bot_content"
down_revision = "0014_wiki_rich_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_texts",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "bot_blocks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("buttons", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("show_in_menu", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("menu_label", sa.String(64), nullable=False, server_default=""),
        sa.Column("command", sa.String(32), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bot_blocks")
    op.drop_table("bot_texts")
