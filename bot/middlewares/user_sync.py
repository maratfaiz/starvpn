"""
UserSyncMiddleware — держит username / full_name пользователя актуальными.

Раньше они записывались только при первом /start. Telegram-username можно
сменить, а освободившийся — занять другому человеку, и подарок по
@username (поиск по User.username) мог уйти не тому. Теперь при каждом
апдейте значения сверяются с Telegram, а у других пользователей тот же
username сбрасывается — он однозначно указывает на одного человека.
Работает после DbSessionMiddleware (сессия уже есть в data).
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import func, update

from bot.models.user import User

logger = logging.getLogger(__name__)


class UserSyncMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        session = data.get("session")
        if from_user and session:
            try:
                await sync_user(session, from_user.id, from_user.username, from_user.full_name)
            except Exception:
                logger.exception("User sync failed for tg_id=%s", from_user.id)
                await session.rollback()
        return await handler(event, data)


async def sync_user(session, tg_id: int, username: str | None, full_name: str | None) -> None:
    user = await session.get(User, tg_id)
    if not user:
        return  # новый пользователь — его создаст /start
    username = (username or None) and username[:64]
    changed = False
    if username != user.username:
        if username:
            await release_username(session, username, tg_id)
        user.username = username
        changed = True
    if full_name and full_name[:256] != user.full_name:
        user.full_name = full_name[:256]
        changed = True
    if changed:
        await session.commit()


async def release_username(session, username: str, owner_id: int) -> None:
    """Сбросить username у всех, кроме owner_id (Telegram отдал его новому владельцу)."""
    await session.execute(
        update(User)
        .where(func.lower(User.username) == username.lower(), User.telegram_id != owner_id)
        .values(username=None)
    )
