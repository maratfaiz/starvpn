"""
BanMiddleware — блокирует апдейты от забаненных пользователей.
Работает после DbSessionMiddleware (сессия уже есть в data).
"""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from bot.config import settings
from bot.models.user import User


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Получаем from_user из любого типа апдейта
        from_user = getattr(event, "from_user", None)
        tg_id: int | None = from_user.id if from_user else None

        # Администратора не трогаем
        if tg_id and tg_id != settings.telegram_admin_id:
            session = data.get("session")
            if session:
                try:
                    result = await session.execute(
                        select(User.is_banned).where(User.telegram_id == tg_id)
                    )
                    row = result.scalar_one_or_none()
                    if row:  # is_banned == True
                        return  # тихо игнорируем
                except Exception:
                    pass  # если БД недоступна — пропускаем

        return await handler(event, data)
