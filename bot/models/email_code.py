"""Одноразовые коды подтверждения email (регистрация, вход по паролю)."""

from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    # sha256(код) — сам 6-значный код никогда не попадает в БД в открытом виде
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
