"""Простое key-value хранилище настроек, редактируемых из админ-панели
(сейчас — включение/выключение способов оплаты; можно расширять без новых
миграций под каждую новую настройку)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
