"""Сессии веб-админки — bearer-токен, привязанный к конкретному AdminAccount
(раньше "токеном" был сам общий секрет ADMIN_WEB_KEY, без понятия сессии).

username/rank денормализованы сюда, чтобы прогреть in-memory кэш сессий
при старте процесса (bot/utils/admin_auth.py) одним запросом, без JOIN —
админ-панель это внутренний инструмент с редкими логинами, это не
проблема согласованности данных на практике."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    admin_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("admin_accounts.id", ondelete="CASCADE"), index=True
    )
    username: Mapped[str] = mapped_column(String(64))
    rank: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
