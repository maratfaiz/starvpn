"""
SQLAlchemy ORM model — таблица пользователей.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, backref


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Marzban username (tg_{telegram_id})
    marzban_username: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)

    # Referral system
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=True, index=True
    )
    referral_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_days_granted: Mapped[int] = mapped_column(Integer, default=0)

    # Stars paid (сумма в Stars со всех оплаченных инвойсов)
    total_stars_paid: Mapped[int] = mapped_column(Integer, default=0)

    # Учтён ли этот пользователь (как реферал) в счётчике своего реферера —
    # чтобы бонус начислялся один раз за человека, а не при каждой продлении
    referral_bonus_counted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Модерация
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Подписка
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Временны́е метки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    referrals: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[referrer_id],
        backref=backref("referrer", remote_side="User.telegram_id"),
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User tg_id={self.telegram_id} username={self.username}>"
