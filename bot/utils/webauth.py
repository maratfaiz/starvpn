"""
Аутентификация личного кабинета (веб-аккаунт без Telegram): magic-link
вход по email + cookie-сессии.

Пользователи веб-аккаунта — это обычные User с синтетическим отрицательным
telegram_id (см. docstring в bot/models/user.py). Это позволяет им работать
со всей существующей моделью Device/Payment/референкой без изменений.
"""

import hashlib
import logging
import random
import re
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.magic_link import MagicLinkToken
from bot.models.user import User
from bot.models.web_session import WebSession

logger = logging.getLogger(__name__)

MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)
SESSION_COOKIE_NAME = "star_session"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip())) and len(email) <= 320


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_magic_link(email: str, session: AsyncSession) -> str:
    """Создаёт токен, возвращает сырое значение (для письма)."""
    raw = secrets.token_urlsafe(32)
    token = MagicLinkToken(
        email=email.lower().strip(),
        token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + MAGIC_LINK_TTL,
    )
    session.add(token)
    await session.commit()
    return raw


async def _get_or_create_user_by_email(email: str, session: AsyncSession) -> User:
    email = email.lower().strip()
    r = await session.execute(select(User).where(User.email == email))
    user = r.scalar_one_or_none()
    if user:
        return user

    # Синтетический отрицательный telegram_id — реальные Telegram ID всегда
    # положительные, коллизий не бывает. На случай редкого совпадения —
    # retry с новым случайным значением.
    for _ in range(5):
        synthetic_id = -random.randint(1, 2**62)
        user = User(telegram_id=synthetic_id, email=email)
        session.add(user)
        try:
            await session.commit()
            return user
        except IntegrityError:
            await session.rollback()
            continue
    raise RuntimeError("Failed to allocate a synthetic user id after 5 attempts")


async def verify_magic_link(raw_token: str, session: AsyncSession) -> User | None:
    token_hash = _hash_token(raw_token)
    r = await session.execute(
        select(MagicLinkToken).where(MagicLinkToken.token_hash == token_hash)
    )
    token: MagicLinkToken | None = r.scalar_one_or_none()
    if not token or token.used_at is not None or token.expires_at < datetime.utcnow():
        return None

    token.used_at = datetime.utcnow()
    await session.commit()

    return await _get_or_create_user_by_email(token.email, session)


async def create_web_session(user: User, session: AsyncSession) -> str:
    raw = secrets.token_urlsafe(32)
    ws = WebSession(
        token_hash=_hash_token(raw),
        user_id=user.telegram_id,
        expires_at=datetime.utcnow() + SESSION_TTL,
    )
    session.add(ws)
    await session.commit()
    return raw


async def get_session_user(raw_token: str | None, session: AsyncSession) -> User | None:
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    r = await session.execute(select(WebSession).where(WebSession.token_hash == token_hash))
    ws: WebSession | None = r.scalar_one_or_none()
    if not ws or ws.expires_at < datetime.utcnow():
        return None

    r2 = await session.execute(select(User).where(User.telegram_id == ws.user_id))
    return r2.scalar_one_or_none()


async def delete_web_session(raw_token: str, session: AsyncSession) -> None:
    token_hash = _hash_token(raw_token)
    r = await session.execute(select(WebSession).where(WebSession.token_hash == token_hash))
    ws: WebSession | None = r.scalar_one_or_none()
    if ws:
        await session.delete(ws)
        await session.commit()
