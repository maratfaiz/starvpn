"""Сборка страниц /wiki из БД (WikiArticle) по шаблонам landing/wiki/.

- landing/wiki/_article.html — шаблон статьи (шапка, боковое меню, оглавление,
  подвал и JS-виджеты: аккордеоны, вкладки, поиск по FAQ).
- landing/wiki/index.html — главная Wiki, карточки статей подставляются
  на место маркера __WIKI_GROUPS__.
"""

import html
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.app_setting import AppSetting
from bot.models.wiki_article import WikiArticle

logger = logging.getLogger(__name__)

_WIKI_DIR = Path(__file__).resolve().parent.parent.parent / "landing" / "wiki"
_SEED_FILE = Path(__file__).resolve().parent.parent / "data" / "wiki_seed.json"
_SEEDED_KEY = "wiki_seeded"

_LINK_RE = re.compile(r'\[([^\]]+)\]\(((?:https?://|/)[^\s)]+)\)')
_BOLD_RE = re.compile(r'\*\*(.+?)\*\*')
_H2_RE = re.compile(r'<h2\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h2>', re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')


def _inline_markdown(text: str) -> str:
    """Экранирует текст и применяет [текст](url) и **жирный** — для lede."""
    escaped = html.escape(text)
    escaped = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', escaped)
    return _BOLD_RE.sub(lambda m: f'<strong>{m.group(1)}</strong>', escaped)


def _plain(text: str) -> str:
    """Lede без разметки — для meta description и поиска."""
    text = _LINK_RE.sub(lambda m: m.group(1), text)
    return text.replace("**", "")


def _read_minutes(content_html: str) -> int:
    words = len(html.unescape(_TAG_RE.sub(" ", content_html)).split())
    return max(1, round(words / 180))


def _nav_title(a: WikiArticle) -> str:
    return a.short_title or a.title


def group_by_section(articles: list[WikiArticle]) -> list[tuple[str, list[WikiArticle]]]:
    """Разделы в порядке их первой статьи; статьи — по sort_order."""
    groups: dict[str, list[WikiArticle]] = {}
    for a in sorted(articles, key=lambda x: (x.sort_order, x.id or 0)):
        groups.setdefault(a.section, []).append(a)
    return list(groups.items())


def _side_nav(groups: list[tuple[str, list[WikiArticle]]], current_slug: str) -> str:
    if not groups:
        return '    <div class="side-empty">Статей пока нет</div>'
    parts = []
    for section, items in groups:
        links = "\n".join(
            f'        <a class="side-item{" current" if a.slug == current_slug else ""}" '
            f'href="/wiki/{html.escape(a.slug)}">{html.escape(_nav_title(a))}</a>'
            for a in items
        )
        parts.append(
            '    <div class="side-group">\n'
            f'      <div class="side-group-title">{html.escape(section)}</div>\n'
            f'      <div class="side-items">\n{links}\n      </div>\n'
            '    </div>'
        )
    return "\n".join(parts)


def render_wiki_article_page(article: WikiArticle, published: list[WikiArticle]) -> str:
    """published — все опубликованные статьи (для бокового меню)."""
    tpl = (_WIKI_DIR / "_article.html").read_text(encoding="utf-8")
    updated = (article.updated_at or datetime.utcnow()).strftime("%m.%Y")
    title = html.escape(article.title)
    head = (
        f'    <div class="crumbs"><a href="/wiki">Wiki</a><span>/</span>'
        f'<span>{html.escape(article.section)}</span><span>/</span>'
        f'<span style="color:var(--text2)">{html.escape(_nav_title(article))}</span></div>\n'
        f'    <h1>{title}</h1>\n'
        + (f'    <p class="lede">{_inline_markdown(article.lede)}</p>\n' if article.lede else "")
        + f'    <div class="doc-meta-row"><span>{_read_minutes(article.content_html)} мин чтения</span>'
        f'<span>·</span><span>{html.escape(article.section)}</span><span>·</span>'
        f'<span>обновлено {updated}</span></div>\n\n'
    )
    toc = [(hid, html.unescape(_TAG_RE.sub("", label)).strip())
           for hid, label in _H2_RE.findall(article.content_html)]
    toc_html = "\n".join(
        f'      <a href="#{html.escape(hid)}">{html.escape(label)}</a>' for hid, label in toc
    )
    groups = group_by_section(published)

    # Порядок замен важен: пользовательский контент подставляется последним,
    # чтобы текст статьи, случайно содержащий маркер, ничего не сломал.
    page = (
        tpl.replace("__WIKI_TITLE__", title)
        .replace("__WIKI_DESCRIPTION__", html.escape(_plain(article.lede)))
        .replace("__WIKI_TOC_HIDDEN__", "" if toc else ' style="visibility:hidden"')
        .replace("__WIKI_SIDENAV__", _side_nav(groups, article.slug))
        .replace("__WIKI_TOC__", toc_html)
    )
    # </style> внутри CSS закрыл бы тег раньше времени.
    page = page.replace("/*__WIKI_CUSTOM_CSS__*/", article.custom_css.replace("</", "<\\/"))
    return page.replace("__WIKI_ARTICLE__", head + article.content_html)


def render_wiki_index_page(published: list[WikiArticle]) -> str:
    tpl = (_WIKI_DIR / "index.html").read_text(encoding="utf-8")
    parts = []
    for i, (section, items) in enumerate(group_by_section(published)):
        cards = "\n".join(
            f'      <a class="article-card" href="/wiki/{html.escape(a.slug)}" '
            f'data-kw="{html.escape(a.keywords)}">\n'
            f'        <span class="article-title">{html.escape(_nav_title(a))}</span>\n'
            f'        <span class="article-text">{html.escape(_plain(a.lede))}</span>\n'
            f'        <span class="article-meta">{_read_minutes(a.content_html)} мин · '
            f'{html.escape(section.lower())}</span>\n'
            '      </a>'
            for a in items
        )
        style = "" if i == 0 else ' style="margin-top:48px"'
        parts.append(
            f'  <div data-group{style}>\n'
            f'    <div class="group-head"><h2>{html.escape(section)}</h2><div class="group-rule"></div>'
            f'<span class="group-count" data-count></span></div>\n'
            f'    <div class="article-grid">\n{cards}\n    </div>\n'
            '  </div>'
        )
    return tpl.replace("__WIKI_GROUPS__", "\n\n".join(parts))


async def seed_wiki_articles(session: AsyncSession) -> None:
    """Один раз заливает базовые статьи из bot/data/wiki_seed.json.

    Флаг wiki_seeded в app_settings ставится после первой заливки, поэтому
    статьи, удалённые в админке, при следующем рестарте не вернутся.
    Статьи, чей slug уже занят, пропускаются.
    """
    flag = (await session.execute(
        select(AppSetting).where(AppSetting.key == _SEEDED_KEY)
    )).scalar_one_or_none()
    if flag:
        return

    seed = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
    existing = set((await session.execute(select(WikiArticle.slug))).scalars().all())
    added = 0
    for item in seed:
        if item["slug"] in existing:
            continue
        session.add(WikiArticle(**item, is_published=True))
        added += 1
    session.add(AppSetting(key=_SEEDED_KEY, value="1"))
    await session.commit()
    logger.info("Wiki: залито базовых статей: %d", added)
