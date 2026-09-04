"""
SQLAlchemy ORM model — таблица пользователей.
"""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, backref


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    telegram_id остаётся PK и NOT NULL, но для веб-аккаунтов (вход по email,
    без Telegram) ему присваивается синтетическое отрицательное значение —
    реальные Telegram ID всегда положительные, так что коллизий не бывает.
    Это позволяет email-аккаунтам работать со всей существующей моделью
    (Device/Payment/GiftNotification, реферальная система, Marzban-логика)
    без единой строчки изменений в FK или бизнес-логике. Проверяй
    `user.telegram_id > 0`, чтобы узнать, привязан ли реальный Telegram.
    """

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Веб-аккаунт (личный кабинет без Telegram) — вход по email + паролю.
    email: Mapped[str | None] = mapped_column(String(320), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

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

    # Момент первой реальной оплаты (Stars/карта/крипта, не подарок) — точка
    # отсчёта для 30-дневной выдержки перед начислением бонуса рефереру
    # (см. REFERRAL_VESTING_DAYS в bot/handlers/payment.py). Ставится один
    # раз и не двигается на повторных продлениях.
    first_payment_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Учтён ли этот реферал в выдержке (vesting) своего реферера — True либо
    # после начисления бонуса рефереру, либо после того как реферал не
    # прошёл проверку на 30-й день (перестал быть активным подписчиком).
    # В любом случае обрабатывается один раз, а не при каждой продлении.
    referral_bonus_counted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Модерация
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
