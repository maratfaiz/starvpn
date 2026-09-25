"""
Роли сотрудников админ-панели (раздел «Команда»).

Роль — это название и набор разделов админки, которые она открывает
(sections — ключи через запятую, см. SECTIONS в bot/utils/admin_auth.py).
Главная страница и профиль доступны всем. Ранг 'admin' видит всё и
управляет командой; 'worker' видит только разделы своей роли, без роли —
только главную и профиль.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AdminRole(Base):
    __tablename__ = "admin_roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    sections: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
