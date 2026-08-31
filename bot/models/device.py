"""
Модель устройств пользователя.
Каждое устройство — отдельный пользователь в Marzban с ip_limit=1.
Максимум 3 устройства на пользователя.
"""

from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base

MAX_DEVICES = 3


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)          # 1, 2 или 3
    name: Mapped[str] = mapped_column(String(64), nullable=False)       # тип платформы: "ios" | "android" | ...
    custom_name: Mapped[str | None] = mapped_column(String(64), nullable=True)  # имя, данное пользователем — "Мой iPhone"
    marzban_username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Device #{self.id} tg={self.telegram_id} slot={self.slot} name={self.name!r}>"
