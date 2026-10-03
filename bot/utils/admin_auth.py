"""
Аутентификация веб-админки: логин/пароль на аккаунт (AdminAccount) вместо
общего ADMIN_WEB_KEY на всех. См. ADR-009 в AGENTS/decisions/ADR.md.

Сессии остаются bearer-токеном в заголовке Authorization (чтобы не
переписывать все существующие вызовы _web_auth() в bot/api.py), но токен
теперь привязан к конкретному аккаунту, а не является самим секретом.
Валидные сессии живут в памяти процесса (бот — один процесс, см. ADR-001)
и в таблице admin_sessions для переживания рестартов — при старте бота
(bot/main.py) кэш прогревается из БД через load_sessions_cache().
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.admin_account import AdminAccount
from bot.models.admin_session import AdminSession
from bot.utils.webauth import hash_password, is_valid_password, verify_password

SESSION_TTL = timedelta(days=30)


@dataclass
class AdminIdentity:
    admin_id: int
    username: str
    rank: str
    expires_at: datetime


_SESSIONS: dict[str, AdminIdentity] = {}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_invite_key() -> str:
    return secrets.token_hex(8)


async def load_sessions_cache(session: AsyncSession) -> None:
    """Прогревает кэш сессий из БД при старте процесса."""
    rows = (await session.execute(select(AdminSession))).scalars().all()
    now = datetime.utcnow()
    for row in rows:
        if row.expires_at > now:
            _SESSIONS[row.token_hash] = AdminIdentity(
                admin_id=row.admin_id, username=row.username, rank=row.rank, expires_at=row.expires_at,
            )


def check_session(authorization: str | None) -> AdminIdentity:
    token = (authorization or "").removeprefix("Bearer ").strip()
    identity = _SESSIONS.get(_hash_token(token)) if token else None
    if not identity or identity.expires_at < datetime.utcnow():
        raise PermissionError("Unauthorized")
    return identity


async def _create_session(admin: AdminAccount, session: AsyncSession) -> str:
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires_at = datetime.utcnow() + SESSION_TTL
    session.add(AdminSession(
        token_hash=token_hash, admin_id=admin.id, username=admin.username,
        rank=admin.rank, expires_at=expires_at,
    ))
    await session.commit()
    _SESSIONS[token_hash] = AdminIdentity(admin.id, admin.username, admin.rank, expires_at)
    return raw


async def register_admin(
    invite_key: str, username: str, password: str, session: AsyncSession
) -> tuple[AdminAccount, str]:
    """Создаёт аккаунт админ-панели по инвайт-ключу.

    Мастер-ключ (settings.admin_web_key) даёт ранг 'admin' с собственным
    invite_key для будущих приглашений. Личный invite_key существующего
    'admin' даёт ранг 'worker' (без права приглашать дальше).
    Поднимает ValueError("bad_invite_key" | "username_taken")."""
    username = username.strip()
    if not is_valid_password(password):
        raise ValueError("bad_password")

    existing = (await session.execute(
        select(AdminAccount).where(AdminAccount.username == username)
    )).scalar_one_or_none()
    if existing:
        raise ValueError("username_taken")

    invite_key = invite_key.strip()
    inviter: AdminAccount | None = None
    if settings.admin_web_key and hmac.compare_digest(invite_key, settings.admin_web_key):
        rank = "admin"
    else:
        inviter = (await session.execute(
            select(AdminAccount).where(
                AdminAccount.rank == "admin", AdminAccount.invite_key == invite_key
            )
        )).scalar_one_or_none()
        if not inviter:
            raise ValueError("bad_invite_key")
        rank = "worker"

    admin = AdminAccount(
        username=username,
        password_hash=await hash_password(password),
        rank=rank,
        invite_key=_new_invite_key() if rank == "admin" else None,
        invited_by_id=inviter.id if inviter else None,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    token = await _create_session(admin, session)
    return admin, token


async def login_admin(
    username: str, password: str, session: AsyncSession
) -> tuple[AdminAccount, str] | None:
    username = username.strip()
    admin = (await session.execute(
        select(AdminAccount).where(AdminAccount.username == username)
    )).scalar_one_or_none()
    if not admin or not await verify_password(password, admin.password_hash):
        return None
    token = await _create_session(admin, session)
    return admin, token


async def logout_admin(authorization: str | None, session: AsyncSession) -> None:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        return
    token_hash = _hash_token(token)
    _SESSIONS.pop(token_hash, None)
    row = (await session.execute(
        select(AdminSession).where(AdminSession.token_hash == token_hash)
    )).scalar_one_or_none()
    if row:
        await session.delete(row)
        await session.commit()
