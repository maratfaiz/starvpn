"""
Wiki-статьи — все статьи /wiki живут здесь и редактируются из админ-панели.

Раньше 11 базовых статей были статичными файлами в landing/wiki/, а таблица
была только для новых. Теперь статичных статей нет: они перенесены сюда
(bot/data/wiki_seed.json, заливаются один раз при первом старте — см.
bot/utils/wiki_page.seed_wiki_articles), и любую можно отредактировать или
удалить из /admin → Wiki. Страница собирается по шаблону
landing/wiki/_article.html.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class WikiArticle(Base):
    __tablename__ = "wiki_articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # Короткое название для бокового меню и карточки на /wiki; пусто → title.
    short_title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    # Подзаголовок под h1 и текст карточки. Поддерживает [текст](url), **жирный**.
    lede: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    # Тело статьи — HTML из визуального редактора админки. Пишут его только
    # сотрудники с доступом к /admin, поэтому вставляется в страницу как есть.
    content_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Стили компонентов, которые нужны только этой статье (у перенесённых
    # статей — их исходный CSS). У новых статей обычно пусто.
    custom_css: Mapped[str] = mapped_column(Text, nullable=False, default="")
    section: Mapped[str] = mapped_column(String(64), nullable=False, default="О сервисе")
    keywords: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    # Порядок в меню и на /wiki (по возрастанию); разделы идут в порядке
    # своей первой статьи.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
