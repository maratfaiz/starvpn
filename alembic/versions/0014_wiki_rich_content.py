"""wiki_articles: HTML-контент вместо markdown-body, короткое название, порядок, CSS

Все статьи /wiki теперь в БД (раньше базовые были статичными файлами).
Существующие markdown-тела конвертируются в HTML тем же рендером, которым
они отдавались на сайте, после чего колонка body удаляется.

Revision ID: 0014_wiki_rich_content
Revises: 0013_device_custom_name
Create Date: 2026-09-25
"""
import html
import re

from alembic import op
import sqlalchemy as sa

revision = "0014_wiki_rich_content"
down_revision = "0013_device_custom_name"
branch_labels = None
depends_on = None

_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_ITALIC_RE = re.compile(r'(?<!\*)\*([^*\n]+?)\*(?!\*)')


def _inline(text: str) -> str:
    text = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>', text)
    text = _BOLD_RE.sub(lambda m: f'<strong>{m.group(1)}</strong>', text)
    return _ITALIC_RE.sub(lambda m: f'<em>{m.group(1)}</em>', text)


def _markdown_to_html(body: str) -> str:
    """Копия прежнего bot.utils.wiki_page._render_body (на момент миграции)."""
    parts = []
    for block in body.split("\n\n"):
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith("- ") or ln.startswith("* ") for ln in lines):
            items = "".join(f"<li>{_inline(html.escape(ln[2:].strip()))}</li>" for ln in lines)
            parts.append(f"<ul>{items}</ul>")
        else:
            escaped = html.escape(block.strip()).replace("\n", "<br>")
            parts.append(f"<p>{_inline(escaped)}</p>")
    return "\n".join(parts)


def upgrade() -> None:
    op.add_column("wiki_articles", sa.Column("short_title", sa.String(120), nullable=False, server_default=""))
    op.add_column("wiki_articles", sa.Column("content_html", sa.Text(), nullable=False, server_default=""))
    op.add_column("wiki_articles", sa.Column("custom_css", sa.Text(), nullable=False, server_default=""))
    op.add_column("wiki_articles", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, body FROM wiki_articles")).fetchall()
    for row_id, body in rows:
        conn.execute(
            sa.text("UPDATE wiki_articles SET content_html = :html, sort_order = :so WHERE id = :id"),
            {"html": _markdown_to_html(body or ""), "so": 1000 + row_id, "id": row_id},
        )
    op.drop_column("wiki_articles", "body")


def downgrade() -> None:
    # HTML обратно в markdown не превращается — тело статей теряется.
    op.add_column("wiki_articles", sa.Column("body", sa.String(20000), nullable=False, server_default=""))
    op.drop_column("wiki_articles", "sort_order")
    op.drop_column("wiki_articles", "custom_css")
    op.drop_column("wiki_articles", "content_html")
    op.drop_column("wiki_articles", "short_title")
