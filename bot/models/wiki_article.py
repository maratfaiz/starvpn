"""
Wiki-статьи, создаваемые из админ-панели (CRUD).

Семь исходных статей (VLESS+Reality, Zero Logs, оплата, пробный период,
рефералы, неполадки, FAQ) остаются статичными файлами в landing/wiki/ —
они уже написаны и вычитаны вручную, переносить их в БД незачем и рискованно.
Эта таблица — для новых статей, которые появятся после запуска, через
админку, без деплоя кода. /wiki/{slug} сначала проверяет статичные файлы,
и только если там нет совпадения — ищет здесь.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class WikiArticle(Base):
    __tablename__ = "wiki_articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    lede: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    # Тело статьи: обычный текст, абзацы разделены пустой строкой —
    # рендерится в <p> на лету, без произвольного HTML/markdown-движка.
    body: Mapped[str] = mapped_column(String(20000), nullable=False, default="")
    section: Mapped[str] = mapped_column(String(64), nullable=False, default="О сервисе")
    keywords: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
