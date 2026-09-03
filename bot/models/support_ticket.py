"""
Тикеты поддержки — форма на /support (без входа в аккаунт — контакт
указывается прямо в форме) и из личного кабинета (user_id резолвится
автоматически, если пользователь вошёл).

Сама переписка живёт в `support_ticket_messages` (см. SupportTicketMessage) —
эта таблица хранит только карточку заявки: кто, о чём, какой приоритет,
кому назначена и когда было последнее сообщение (для сортировки/бейджа
"есть новое" в админке, чтобы не джойнить со всей историей на каждый список).
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
    # Исходный текст обращения — снимок для быстрого списка в админке, без
    # похода в support_ticket_messages. Он же дублируется первым сообщением
    # треда (см. create_support_ticket в bot/api.py).
    message: Mapped[str] = mapped_column(String(4000), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # open | answered | closed
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False, index=True)
    # low | normal | urgent
    priority: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    assigned_admin_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("admin_accounts.id"), nullable=True
    )
    # Денормализовано из support_ticket_messages — кто и когда написал
    # последним, чтобы список тикетов в админке считался одним SELECT без
    # join'а на историю сообщений (бейдж "новое от клиента" = sender == 'user').
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_message_sender: Mapped[str] = mapped_column(String(16), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
