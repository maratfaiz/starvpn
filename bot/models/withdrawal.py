"""
Модель для запросов на вывод партнёрских Stars.
"""

from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True
    )
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending → approved / rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Withdrawal id={self.id} tg={self.telegram_id} {self.stars_amount}⭐ {self.status}>"
