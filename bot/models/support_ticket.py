"""
Тикеты поддержки — форма на /support (без входа в аккаунт — контакт
указывается прямо в форме) и из личного кабинета (user_id резолвится
автоматически, если пользователь вошёл).
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # NULL для анонимных обращений — форма /support не требует входа.
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=True, index=True
    )
    # email или @username — как связаться с автором. Обязателен для анонимных
    # обращений (когда user_id пуст); для вошедших дублирует контакт, но
    # user_id остаётся источником истины для авто-уведомления об ответе.
    contact: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # connect | payment | account | other
    topic: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    message: Mapped[str] = mapped_column(String(4000), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # open | answered | closed
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False, index=True)
    admin_reply: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
