"""Рекламный баннер на верхней полосе главной страницы — редактируется из
админ-панели (раздел "Реклама"), без деплоя. Одна строка-синглтон
(id всегда 1) — баннер один на весь сайт, история версий не нужна."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AdBanner(Base):
    __tablename__ = "ad_banner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(String(300), default="")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Ключ из фиксированного набора иконок (см. BANNER_ICONS в bot/api.py и
    # одноимённый JS-объект в landing/index.html + admin/index.html) —
    # не произвольный SVG/URL, чтобы не пришлось думать о XSS в баннере.
    icon: Mapped[str] = mapped_column(String(24), default="sparkle")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
