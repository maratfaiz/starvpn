"""wiki_articles — CRUD-статьи, создаваемые из админ-панели

Revision ID: 0005_wiki_articles
Revises: 0004_support_ticket_redesign
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_wiki_articles"
down_revision = "0004_support_ticket_redesign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wiki_articles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("lede", sa.String(400), nullable=False, server_default=""),
        sa.Column("body", sa.String(20000), nullable=False, server_default=""),
        sa.Column("section", sa.String(64), nullable=False, server_default="О сервисе"),
        sa.Column("keywords", sa.String(300), nullable=False, server_default=""),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_wiki_articles_slug", "wiki_articles", ["slug"])


def downgrade() -> None:
    op.drop_table("wiki_articles")
