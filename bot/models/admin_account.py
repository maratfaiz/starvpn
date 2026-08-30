"""
Аккаунты веб-админки — логин/пароль на человека вместо общего ADMIN_WEB_KEY
на всех. Два ранга (см. ADR-009 в AGENTS/decisions/ADR.md):

- 'admin'  — полный доступ + может пригласить нового человека своим личным
  invite_key (тот получит ранг 'worker').
- 'worker' — доступ к панели, но не может никого пригласить.

Первый аккаунт (ранг 'admin') создаётся через мастер-ключ ADMIN_WEB_KEY —
тот самый секрет, который раньше был единственным способом входа — он один
раз используется как invite_key при регистрации. Дальше каждый 'admin'
приглашает через свой персональный invite_key.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rank: Mapped[str] = mapped_column(String(16))  # 'admin' | 'worker'
    # Личный ключ приглашения — только у ранга 'admin' ('worker' всегда NULL,
    # он не может никого приглашать). Хранится в открытом виде — это код для
    # шэринга (как реферальный код), а не секрет уровня пароля: максимум,
    # что даёт утечка — кто-то сам зарегистрируется рангом 'worker'.
    invite_key: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    invited_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("admin_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
