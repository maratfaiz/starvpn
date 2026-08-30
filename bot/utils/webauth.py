"""
Аутентификация личного кабинета (веб-аккаунт без Telegram): email + пароль,
подтверждение почты одноразовым кодом, cookie-сессии.

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

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.email_code import EmailVerificationCode
from bot.models.user import User
from bot.models.web_session import WebSession

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=15)
CODE_RESEND_COOLDOWN = timedelta(seconds=45)
CODE_MAX_ATTEMPTS = 5
SESSION_TTL = timedelta(days=30)
SESSION_COOKIE_NAME = "star_session"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email.strip())) and len(email) <= 320


def is_valid_password(password: str) -> bool:
    return 8 <= len(password) <= 128


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # повреждённый/незнакомый формат хэша — считаем паролем неверным
        return False


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


def _generate_code() -> str:
    """6-значный числовой код, криптографически случайный."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_verification_code(email: str, session: AsyncSession) -> str:
    """Создаёт код подтверждения для email, возвращает сырое значение (для письма).
    Если для этого email недавно уже был выслан код — не шлём новый чаще,
    чем раз в CODE_RESEND_COOLDOWN (защита от спама себе на почту)."""
    email = email.lower().strip()
    r = await session.execute(
        select(EmailVerificationCode)
        .where(EmailVerificationCode.email == email, EmailVerificationCode.used_at.is_(None))
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    last: EmailVerificationCode | None = r.scalar_one_or_none()
    if last and last.created_at > datetime.utcnow() - CODE_RESEND_COOLDOWN:
        raise ValueError("too_soon")

    raw = _generate_code()
    code = EmailVerificationCode(
        email=email,
        code_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + CODE_TTL,
    )
    session.add(code)
    await session.commit()
    return raw


async def check_verification_code(email: str, raw_code: str, session: AsyncSession) -> bool:
    """Проверяет код, помечает использованным при успехе. Ограничивает число
    попыток на один код, чтобы код нельзя было перебрать."""
    email = email.lower().strip()
    r = await session.execute(
        select(EmailVerificationCode)
        .where(EmailVerificationCode.email == email, EmailVerificationCode.used_at.is_(None))
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    code: EmailVerificationCode | None = r.scalar_one_or_none()
    if not code or code.expires_at < datetime.utcnow() or code.attempts >= CODE_MAX_ATTEMPTS:
        return False

    if _hash_token(raw_code.strip()) != code.code_hash:
        code.attempts += 1
        await session.commit()
        return False

    code.used_at = datetime.utcnow()
    await session.commit()
    return True


async def register_user(email: str, password: str, session: AsyncSession) -> User:
    """Создаёт (или переиспользует ещё не подтверждённый) веб-аккаунт с паролем.
    Если email уже подтверждён — вызывающий код должен был это проверить
    заранее (см. /api/account/register)."""
    email = email.lower().strip()
    user = await _get_or_create_user_by_email(email, session)
    user.password_hash = hash_password(password)
    await session.commit()
    return user


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
