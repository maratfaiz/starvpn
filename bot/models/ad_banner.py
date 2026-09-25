"""Баннер на верхней полосе главной страницы — редактируется из
админ-панели (раздел «Баннер»), без деплоя. Одна строка-синглтон
(id всегда 1) — баннер один на весь сайт, история версий не нужна."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AdBanner(Base):
    __tablename__ = "ad_banner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    text: Mapped[str] = mapped_column(String(300), default="")
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Ключ из фиксированного набора иконок (BANNER_ICONS в bot/utils/banner.py) —
    # не произвольный SVG/URL, чтобы не пришлось думать о XSS в баннере.
    icon: Mapped[str] = mapped_column(String(24), default="sparkle")
    # Своя картинка-иконка (MediaFile.id) — если задана, вместо icon.
    icon_media_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Оформление полосы: ключ из BANNER_STYLES (bot/utils/banner.py).
    style: Mapped[str] = mapped_column(String(16), default="gold")
    # Показывать только в этом промежутке (UTC); пусто — без ограничений.
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Таймер «до конца акции» — только если задан ends_at.
    show_countdown: Mapped[bool] = mapped_column(Boolean, default=False)
    # Крестик: скрытый баннер не показывается посетителю до следующей правки.
    dismissible: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
