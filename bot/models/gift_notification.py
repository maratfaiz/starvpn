"""
Уведомление о подарке — показывается один раз в мини-приложении.
"""
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from bot.models.user import Base


class GiftNotification(Base):
    __tablename__ = "gift_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), index=True
    )
    sender_name: Mapped[str] = mapped_column(String(128))
    plan_label: Mapped[str] = mapped_column(String(64))
    plan_days: Mapped[int] = mapped_column(Integer)
    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
