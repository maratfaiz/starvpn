"""Включение/выключение VPN-доступа пользователя целиком — все его устройства.

Раньше бан и разбан трогали только user.marzban_username (старую схему
«один аккаунт на человека»), а устройства (текущая схема, bot/models/device.py)
продолжали работать — забаненный пользователь сохранял VPN.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.device import Device
from bot.models.user import User
from bot.utils.marzban import marzban

logger = logging.getLogger(__name__)


async def marzban_usernames(user: User, session: AsyncSession) -> list[str]:
    rows = await session.execute(
        select(Device.marzban_username).where(
            Device.telegram_id == user.telegram_id, Device.is_active.is_(True)
        )
    )
    names = list(rows.scalars().all())
    if user.marzban_username and user.marzban_username not in names:
        names.append(user.marzban_username)
    return names


async def set_vpn_enabled(user: User, session: AsyncSession, enabled: bool) -> None:
    for name in await marzban_usernames(user, session):
        try:
            if enabled:
                await marzban.enable_user(name)
            else:
                await marzban.disable_user(name)
        except Exception as e:
            logger.warning("Marzban %s %s failed: %s", "enable" if enabled else "disable", name, e)
