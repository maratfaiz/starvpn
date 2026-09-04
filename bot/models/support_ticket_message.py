"""Support ticket thread — one row per message in a ticket's back-and-forth.

Replaces the old single SupportTicket.admin_reply field (could hold exactly
one reply, ever). The ticket's original text is inserted here as message #1
at creation time, so the whole conversation — including the very first
message — lives in one place.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 'user' | 'admin'
    sender: Mapped[str] = mapped_column(String(16), nullable=False)
    # Кто из админки ответил — NULL для сообщений автора тикета.
    admin_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("admin_accounts.id"), nullable=True)
    admin_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
