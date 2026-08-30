"""Payment records — one row per created invoice."""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # получатель подписки — для подарка это НЕ плательщик, а тот, кому дарят
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # pending | paid | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    # stars | crypto
    payment_method: Mapped[str] = mapped_column(String(16), default="stars", nullable=False)
    # USDT | TON | BTC | ETH — только для crypto-платежей
    asset: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # CryptoPay invoice_id — только для crypto-платежей
    invoice_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    # количество дней, которые будут выданы после оплаты
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # подарок с сайта — telegram_id это получатель, gift_sender_id это плательщик
    is_gift: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gift_sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gift_anon: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gift_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # подарок по ссылке — получатель неизвестен при создании платежа, поэтому
    # telegram_id временно = gift_sender_id, пока подарок не заберут по коду.
    gift_link_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    gift_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        method = self.payment_method or "stars"
        return f"<Payment order={self.order_id} tg={self.telegram_id} {self.amount} {method} {self.status}>"
