"""
User dashboard — "📊 Мой статус" and "🔗 Моё подключение".

Shows: subscription status, days remaining, traffic used/limit, balance.
"🔗 Моё подключение" resends the VLESS link + fresh QR code.
"""

import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.config import settings
from bot.models.user import User
from bot.models.device import Device
from bot.utils.marzban import marzban
from bot.utils.qr import make_qr_photo

router = Router()
logger = logging.getLogger(__name__)


def _bytes_to_gb(b: int | None) -> str:
    if not b:
        return "0 ГБ"
    return f"{b / 1_073_741_824:.2f} ГБ"


def _days_remaining(expires_at: datetime | None) -> str:
    if not expires_at:
        return "нет активной подписки"
    now = datetime.utcnow()
    delta = expires_at - now
    if delta.total_seconds() <= 0:
        return "подписка истекла"
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days} дн. {hours} ч."
    return f"{hours} ч."


@router.message(F.text == "📊 Мой статус")
async def my_status(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await message.answer("Сначала отправь /start.")
        return

    if not user.marzban_username:
        await message.answer(
            "📊 <b>Твой статус</b>\n\n"
            "🔴 Подписка: <b>не активна</b>\n\n"
            "Нажми <b>🎁 Попробовать бесплатно</b> или <b>⚡️ Купить подписку</b>.",
            parse_mode="HTML",
        )
        return

    try:
        mz = await marzban.get_user(user.marzban_username)
    except Exception as e:
        logger.error("Marzban get_user failed for %s: %s", user.marzban_username, e)
        await message.answer("⚠️ Не удалось получить данные от VPN-сервера. Попробуй позже.")
        return

    status = mz.get("status", "unknown")
    used_traffic = mz.get("used_traffic", 0)
    data_limit = mz.get("data_limit", 0)
    expire_ts = mz.get("expire")
    expires_at = datetime.utcfromtimestamp(expire_ts) if expire_ts else None

    status_icon = "🟢" if status == "active" else "🔴"
    status_ru = {
        "active": "активна",
        "expired": "истекла",
        "disabled": "отключена",
        "limited": "лимит трафика",
    }.get(status, status)

    traffic_line = (
        f"{_bytes_to_gb(used_traffic)} / {_bytes_to_gb(data_limit)}"
        if data_limit
        else f"{_bytes_to_gb(used_traffic)} (без лимита)"
    )

    await message.answer(
        f"📊 <b>Твой статус</b>\n\n"
        f"{status_icon} Подписка: <b>{status_ru}</b>\n"
        f"⏳ Осталось: <b>{_days_remaining(expires_at)}</b>\n"
        f"📡 Трафик: <b>{traffic_line}</b>",
        parse_mode="HTML",
    )


@router.message(F.text == "🔗 Моё подключение")
async def my_connection(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await message.answer(
            "У тебя нет активного VPN-аккаунта.\n"
            "Нажми <b>🎁 Попробовать бесплатно</b> или <b>⚡️ Купить подписку</b>.",
            parse_mode="HTML",
        )
        return

    # Берём первое активное устройство; если нет — основной аккаунт пользователя
    mz_username = None
    dev_name = "VPN"
    dev_r = await session.execute(
        select(Device)
        .where(Device.telegram_id == tg_id, Device.is_active.is_(True))
        .order_by(Device.slot)
        .limit(1)
    )
    dev = dev_r.scalar_one_or_none()
    if dev:
        mz_username = dev.marzban_username
        dev_name = dev.name
    elif user.marzban_username:
        mz_username = user.marzban_username

    if not mz_username:
        await message.answer(
            "У тебя нет активного VPN-аккаунта.\n"
            "Нажми <b>🎁 Попробовать бесплатно</b> или <b>⚡️ Купить подписку</b>.",
            parse_mode="HTML",
        )
        return

    try:
        now = datetime.utcnow()
        exp = user.subscription_expires_at
        days_left = max(1, (exp - now).days) if exp and exp > now else 30
        mz = await marzban.get_or_create_user(mz_username, tg_id, days_left)
        link = marzban.extract_vless_link(mz)
    except Exception as e:
        logger.error("Marzban get_or_create failed for %s: %s", mz_username, e)
        await message.answer("⚠️ Не удалось получить ссылку. Попробуй позже.")
        return

    if not link:
        await message.answer(
            f"⚠️ Ссылка недоступна. Обратись в поддержку: {settings.support_username}"
        )
        return

    qr = make_qr_photo(link, "vpn_qr.png")
    await message.answer_photo(
        qr,
        caption=(
            f"🔑 <b>{dev_name}</b>\n\n"
            f"<code>{link}</code>\n\n"
            "📲 Импортируй ссылку в Streisand (iOS) или v2rayNG (Android)."
        ),
        parse_mode="HTML",
    )
