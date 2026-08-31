"""Referral credit ledger — one row per bonus grant to a referrer.

This is the audit trail the old system never had (only a running total on
User.extra_days_granted), and the basis for the rolling 365-day cap on how
many referral days a single referrer can earn.
"""

from datetime import datetime
from sqlalchemy import BigInteger, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class ReferralCredit(Base):
    __tablename__ = "referral_credits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True
    )
    referred_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<ReferralCredit referrer={self.referrer_id} referred={self.referred_id} days={self.days}>"
