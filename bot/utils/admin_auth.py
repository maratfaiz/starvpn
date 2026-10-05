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

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.admin_account import AdminAccount
from bot.models.admin_role import AdminRole
from bot.models.admin_session import AdminSession
from bot.models.app_setting import AppSetting
from bot.utils.webauth import hash_password, is_valid_password, verify_password

SESSION_TTL = timedelta(days=30)


@dataclass
class AdminIdentity:
    admin_id: int
    username: str
    rank: str
    expires_at: datetime


_SESSIONS: dict[str, AdminIdentity] = {}

# ── Права доступа по разделам ────────────────────────────────────────────────
# Ключи совпадают с id разделов в admin/index.html. Главная и профиль
# доступны всем, «Команда» — только рангу 'admin'.
SECTIONS: dict[str, str] = {
    "users": "Аккаунты",
    "devices": "Устройства",
    "servers": "Серверы",
    "payments": "Платежи",
    "referrals": "Рефералы",
    "support": "Обращения",
    "bot": "Бот",
    "wiki": "Wiki",
    "banner": "Баннер",
    "settings": "Настройки",
}
ALWAYS_ALLOWED = {"dash", "profile"}

# Роли по умолчанию — создаются один раз (seed_roles); админ может менять.
PRESET_ROLES = [
    ("Полный доступ", "Все разделы, кроме управления командой", list(SECTIONS)),
    ("Писатель блога", "Только статьи Wiki", ["wiki"]),
    ("Поддержка", "Обращения и карточки пользователей", ["support", "users", "devices"]),
    ("Контент-менеджер", "Тексты бота, Wiki и баннер", ["bot", "wiki", "banner"]),
]

# Кэш аккаунтов и ролей: admin_id → (rank, role_id, is_active), role_id → разделы.
_ACCOUNTS: dict[int, tuple[str, int | None, bool]] = {}
_ROLES: dict[int, frozenset[str]] = {}


def parse_sections(raw: str) -> list[str]:
    return [s for s in (raw or "").split(",") if s in SECTIONS]


async def refresh_access_cache(session: AsyncSession) -> None:
    """Перечитать роли и аккаунты — после любой правки в разделе «Команда»."""
    global _ACCOUNTS, _ROLES
    roles = (await session.execute(select(AdminRole))).scalars().all()
    _ROLES = {r.id: frozenset(parse_sections(r.sections)) for r in roles}
    accounts = (await session.execute(select(AdminAccount))).scalars().all()
    _ACCOUNTS = {a.id: (a.rank, a.role_id, bool(a.is_active)) for a in accounts}


def allowed_sections(identity: "AdminIdentity") -> set[str]:
    rank, role_id, _ = _ACCOUNTS.get(identity.admin_id, (identity.rank, None, True))
    if rank == "admin":
        return set(SECTIONS) | ALWAYS_ALLOWED | {"staff"}
    return set(_ROLES.get(role_id, frozenset())) | ALWAYS_ALLOWED


def can(identity: "AdminIdentity", *sections: str) -> bool:
    """True, если доступен хотя бы один из перечисленных разделов."""
    allowed = allowed_sections(identity)
    return any(s in allowed for s in sections)


async def seed_roles(session: AsyncSession) -> None:
    """Один раз создаёт роли по умолчанию. Сотрудникам, которые были до
    появления ролей (у них был доступ ко всему), выдаётся «Полный доступ» —
    чтобы после обновления у них ничего не пропало."""
    flag = await session.get(AppSetting, "roles_seeded")
    if flag:
        return
    existing = {r.name: r for r in (await session.execute(select(AdminRole))).scalars().all()}
    for name, desc, sections in PRESET_ROLES:
        if name not in existing:
            existing[name] = AdminRole(name=name, description=desc, sections=",".join(sections))
            session.add(existing[name])
    await session.flush()
    full = existing["Полный доступ"]
    workers = (await session.execute(
        select(AdminAccount).where(AdminAccount.rank == "worker", AdminAccount.role_id.is_(None))
    )).scalars().all()
    for w in workers:
        w.role_id = full.id
    session.add(AppSetting(key="roles_seeded", value="1"))
    await session.commit()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_invite_key() -> str:
    return secrets.token_hex(8)


async def load_sessions_cache(session: AsyncSession) -> None:
    """Прогревает кэш сессий, аккаунтов и ролей из БД при старте процесса."""
    await refresh_access_cache(session)
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
    account = _ACCOUNTS.get(identity.admin_id)
    if account is not None and not account[2]:
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
        password_hash=hash_password(password),
        rank=rank,
        invite_key=_new_invite_key() if rank == "admin" else None,
        invited_by_id=inviter.id if inviter else None,
        last_login_at=datetime.utcnow(),
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    # Новый сотрудник — без роли (видит только главную и профиль), пока
    # админ не выдаст роль в разделе «Команда».
    await refresh_access_cache(session)

    token = await _create_session(admin, session)
    return admin, token


async def login_admin(
    username: str, password: str, session: AsyncSession
) -> tuple[AdminAccount, str] | None:
    username = username.strip()
    admin = (await session.execute(
        select(AdminAccount).where(AdminAccount.username == username)
    )).scalar_one_or_none()
    if not admin or not verify_password(password, admin.password_hash):
        return None
    if not admin.is_active:
        raise ValueError("inactive")
    admin.last_login_at = datetime.utcnow()
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


def token_hash_of(authorization: str | None) -> str:
    return _hash_token((authorization or "").removeprefix("Bearer ").strip())


async def list_sessions(admin_id: int, session: AsyncSession) -> list[AdminSession]:
    rows = await session.execute(
        select(AdminSession)
        .where(AdminSession.admin_id == admin_id, AdminSession.expires_at > datetime.utcnow())
        .order_by(AdminSession.created_at.desc())
    )
    return list(rows.scalars().all())


async def revoke_sessions(admin_id: int, session: AsyncSession, keep_hash: str | None = None) -> int:
    """Завершить все сессии аккаунта (кроме keep_hash). Возвращает сколько."""
    rows = await list_sessions(admin_id, session)
    hashes = [r.token_hash for r in rows if r.token_hash != keep_hash]
    for h in hashes:
        _SESSIONS.pop(h, None)
    if hashes:
        await session.execute(delete(AdminSession).where(AdminSession.token_hash.in_(hashes)))
        await session.commit()
    return len(hashes)


async def change_password(admin: AdminAccount, old: str, new: str, session: AsyncSession) -> None:
    if not verify_password(old, admin.password_hash):
        raise ValueError("Текущий пароль указан неверно")
    if not is_valid_password(new):
        raise ValueError("Новый пароль — от 8 до 128 символов")
    admin.password_hash = hash_password(new)
    await session.commit()

