"""Payment records — one row per created invoice."""

from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
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

    def __repr__(self) -> str:
        method = self.payment_method or "stars"
        return f"<Payment order={self.order_id} tg={self.telegram_id} {self.amount} {method} {self.status}>"
