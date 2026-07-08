"""
Гостевые заказы — покупка VPN-ключа прямо на сайте, без Telegram.

Решает проблему "нет доступа к Telegram без VPN": человек платит
картой на лендинге, ключ выдаётся и показывается сразу на странице
успеха, без необходимости открывать бота.

Полностью отделено от User/telegram_id — marzban_username здесь имеет
формат web_{public_id[:8]}, а не tg_{telegram_id} (см. CLAUDE.md).
"""

from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class GuestOrder(Base):
    __tablename__ = "guest_orders"

    # Целочисленный id нужен только для Robokassa InvId (см. card_payment.py
    # и api.py — там InvId делится по чётности между Payment и GuestOrder,
    # т.к. у Robokassa один общий ResultURL).
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Публичный опаковый идентификатор — используется в URL страницы успеха
    # и при поллинге статуса, чтобы нельзя было подобрать чужой заказ по id.
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    plan_key: Mapped[str] = mapped_column(String(16), nullable=False)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # pending | paid | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)

    marzban_username: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    vless_link: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<GuestOrder public_id={self.public_id} {self.amount} {self.status}>"
