"""
Тексты бота, редактируемые из админки (/admin → Бот).

BotText — переопределения системных текстов и подписей кнопок: ключ из
реестра bot/utils/bot_texts.py → текст. Нет строки — бот говорит текстом
по умолчанию из кода. Ключи вида "hidden:btn.gift" = "1" прячут кнопку
главного меню.

BotBlock — свои блоки, созданные в админке: сообщение + кнопки, которые
ведут на другой блок, на экран бота или на ссылку. Блок можно вынести
в главное меню и/или открывать командой (/команда).
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class BotText(Base):
    __tablename__ = "bot_texts"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class BotBlock(Base):
    __tablename__ = "bot_blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Название блока — видно только в админке.
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    # Текст сообщения (HTML-разметка Telegram).
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # JSON: [{"label": "…", "type": "block"|"screen"|"url", "target": "…"}]
    buttons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # Картинка над текстом: "media:<id>" (загружена в админке) или https://…
    image: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    show_in_menu: Mapped[bool] = mapped_column(Boolean, default=False)
    menu_label: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # Команда без слэша ("help" → /help); пусто — без команды.
    command: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
