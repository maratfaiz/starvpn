"""
User dashboard — "📊 Мой статус" and "🔗 Моё подключение".

Shows: subscription status, days remaining, traffic used/limit, balance.
"🔗 Моё подключение" resends the VLESS link + fresh QR code.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.config import settings
from bot.models.user import User
from bot.models.device import Device
from bot.utils.marzban import marzban
from bot.utils.qr import make_qr_photo
from bot.utils.branding import set_vless_remark, subscription_url

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


async def _resolve_connection(tg_id: int, session: AsyncSession) -> tuple[User | None, str | None, str]:
    """Первое активное устройство; если нет — основной аккаунт пользователя.
    Возвращает (user, mz_username, dev_name)."""
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        return None, None, "VPN"

    dev_r = await session.execute(
        select(Device)
        .where(Device.telegram_id == tg_id, Device.is_active.is_(True))
        .order_by(Device.slot)
        .limit(1)
    )
    dev = dev_r.scalar_one_or_none()
    if dev:
        return user, dev.marzban_username, dev.name
    if user.marzban_username:
        return user, user.marzban_username, "VPN"
    return user, None, "VPN"


_NO_ACCOUNT_TEXT = (
    "У тебя нет активного VPN-аккаунта.\n"
    "Нажми <b>🎁 Попробовать бесплатно</b> или <b>⚡️ Купить подписку</b>."
)


@router.message(F.text == "🔗 Моё подключение")
async def my_connection(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    user, mz_username, dev_name = await _resolve_connection(tg_id, session)

    if not user or not mz_username:
        await message.answer(_NO_ACCOUNT_TEXT, parse_mode="HTML")
        return

    await message.answer(
        f"🔑 <b>{dev_name}</b>\n\n"
        "Получи доступ — вручную (QR/ссылка для вставки в приложение) "
        "или подпиской (сама добавится в Happ, v2rayNG и т.п.):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔑 Ключ", callback_data="conn:key"),
            InlineKeyboardButton(text="🔗 Ссылка", callback_data="conn:sub"),
        ]]),
    )


@router.callback_query(F.data == "conn:key")
async def conn_show_key(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    user, mz_username, dev_name = await _resolve_connection(tg_id, session)
    if not user or not mz_username:
        await callback.answer("Нет активного VPN-аккаунта.", show_alert=True)
        return

    await callback.answer("⏳")
    try:
        now = datetime.utcnow()
        exp = user.subscription_expires_at
        days_left = max(1, (exp - now).days) if exp and exp > now else 30
        mz = await marzban.get_or_create_user(mz_username, tg_id, days_left)
        link = set_vless_remark(marzban.extract_vless_link(mz))
    except Exception as e:
        logger.error("Marzban get_or_create failed for %s: %s", mz_username, e)
        await callback.message.answer("⚠️ Не удалось получить ссылку. Попробуй позже.")
        return

    if not link:
        await callback.message.answer(
            f"⚠️ Ссылка недоступна. Обратись в поддержку: {settings.support_username}"
        )
        return

    qr = make_qr_photo(link, "vpn_qr.png")
    await callback.message.answer_photo(
        qr,
        caption=f"🔑 <b>{dev_name}</b>\n\n<code>{link}</code>\n\n👆 Нажми на ключ, чтобы скопировать",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "conn:sub")
async def conn_show_sublink(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    user, mz_username, dev_name = await _resolve_connection(tg_id, session)
    if not user or not mz_username:
        await callback.answer("Нет активного VPN-аккаунта.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        f"🔗 <b>Ссылка-подписка — {dev_name}</b>\n\n"
        f"<code>{subscription_url(mz_username)}</code>\n\n"
        "Открой в Happ, v2rayNG или другом клиенте — сервер добавится "
        "автоматически под именем «STAR VPN».",
        parse_mode="HTML",
    )
