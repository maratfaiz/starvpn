"""
👤 Моя подписка — личный кабинет пользователя.

Показывает: ID, остаток дней, тариф, дата истечения.
Кнопки:
  🔄 Продлить      — выбор тарифа
  📱 Мои устройства — переход в менеджер устройств
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models.user import User
from bot.utils.marzban import marzban

router = Router()
logger = logging.getLogger(__name__)


# ─────────────────────────── helpers ────────────────────────────────────────

def _days_left(expires: datetime | None) -> tuple[str, str]:
    if not expires:
        return "🔴", "Не активна"
    now = datetime.utcnow()
    if expires < now:
        return "🔴", "Истекла"
    delta = expires - now
    days = delta.days
    hours = delta.seconds // 3600
    if days == 0:
        return "🟡", f"Менее суток ({hours} ч.)"
    return "🟢", f"{days} дн. {hours} ч."



def _subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Устройства", callback_data="sub:devices")],
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="sub:pay_choice")],
    ])


def _pay_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐  Telegram Stars", callback_data="sub:renew")],
        [InlineKeyboardButton(text="💳  Банковская карта  (₽)", callback_data="sub:card")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="sub:back")],
    ])


async def _build_text(user: User) -> str:
    icon, days_str = _days_left(user.subscription_expires_at)
    exp = user.subscription_expires_at
    exp_str = exp.strftime("%d.%m.%Y") if exp else "—"

    return (
        f"📱 <b>Моя подписка</b>\n\n"
        f"{icon} Осталось дней: <b>{days_str}</b>\n"
        f"⏳ Действует до: <b>{exp_str}</b>"
    )


# ─────────────────────────── handlers ───────────────────────────────────────

@router.message(F.text.in_({"📱 Моя подписка", "👤 Моя подписка"}))
async def show_my_subscription(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала отправь /start.")
        return
    await message.answer(
        await _build_text(user),
        parse_mode="HTML",
        reply_markup=_subscription_kb(),
    )


@router.message(F.text == "📱 Мои устройства")
async def show_my_devices(message: Message, session: AsyncSession) -> None:
    """Главная кнопка меню → сразу на экран устройств."""
    from bot.handlers.devices import show_devices_screen
    await show_devices_screen(message, session)


@router.message(F.text == "👤 Профиль")
async def show_profile_legacy(message: Message, session: AsyncSession) -> None:
    await show_my_subscription(message, session)


# ─────────────────────────── callbacks ──────────────────────────────────────

@router.callback_query(F.data == "sub:refresh")
async def refresh_subscription(callback: CallbackQuery, session: AsyncSession) -> None:
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            await _build_text(user), parse_mode="HTML",
            reply_markup=_subscription_kb(),
        )
    except Exception:
        pass
    await callback.answer("Обновлено ✅")


@router.callback_query(F.data == "sub:pay_choice")
async def pay_choice(callback: CallbackQuery) -> None:
    """Выбор способа оплаты — Stars или крипта."""
    await callback.message.edit_text(
        "💳 <b>Выбери способ оплаты</b>",
        parse_mode="HTML",
        reply_markup=_pay_choice_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "sub:renew")
async def sub_renew(callback: CallbackQuery) -> None:
    """Продлить подписку — показываем тарифы."""
    from bot.handlers.payment import PLANS
    buttons = [
        [InlineKeyboardButton(
            text=f"{plan['label']} — {plan['stars']} ⭐",
            callback_data=f"buy:{key}",
        )]
        for key, plan in PLANS.items()
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sub:pay_choice")])
    await callback.message.edit_text(
        "⭐ <b>Оплата Telegram Stars</b>\n\n"
        "Дни добавляются к текущей подписке.\n"
        "Оплата мгновенная — прямо внутри Telegram.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data == "sub:devices")
async def show_devices(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перенаправляет в менеджер устройств."""
    from bot.handlers.devices import show_devices_screen
    await callback.answer()
    await show_devices_screen(callback, session)


@router.callback_query(F.data == "sub:back")
async def back_to_subscription(callback: CallbackQuery, session: AsyncSession) -> None:
    """Возврат к экрану 'Моя подписка'."""
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user: User | None = result.scalar_one_or_none()
    if not user:
        await callback.answer()
        return
    try:
        await callback.message.edit_text(await _build_text(user), parse_mode="HTML", reply_markup=_subscription_kb())
    except Exception:
        await callback.message.answer(await _build_text(user), parse_mode="HTML", reply_markup=_subscription_kb())
    await callback.answer()


@router.callback_query(F.data == "sub:link")
async def show_link(callback: CallbackQuery, session: AsyncSession) -> None:
    from bot.utils.qr import make_qr_photo
    from bot.models.device import Device
    tg_id = callback.from_user.id

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    # Берём первое активное устройство
    from bot.models.device import Device
    dev_r = await session.execute(
        select(Device).where(Device.telegram_id == tg_id, Device.is_active.is_(True))
        .order_by(Device.slot).limit(1)
    )
    dev = dev_r.scalar_one_or_none()

    # Fallback: основной аккаунт только если устройств нет
    mz_username = dev.marzban_username if dev else user.marzban_username

    if not mz_username:
        await callback.answer("Нет активного VPN-аккаунта.", show_alert=True)
        return

    try:
        now = datetime.utcnow()
        exp = user.subscription_expires_at
        days_left = max(1, (exp - now).days) if exp and exp > now else 30
        mz = await marzban.get_or_create_user(mz_username, tg_id, days_left)
    except Exception as e:
        logger.error("Marzban error for %s: %s", mz_username, e)
        await callback.answer("Ошибка получения ссылки.", show_alert=True)
        return

    link = marzban.extract_vless_link(mz)
    if not link:
        await callback.answer("Ссылка недоступна — обратись в поддержку.", show_alert=True)
        return

    from bot.handlers.payment import _instructions_kb
    qr = make_qr_photo(link, "vpn_qr.png")
    await callback.message.answer_photo(
        qr,
        caption=(
            "🔑 <b>Ваш ключ</b>\n\n"
            f"<code>{link}</code>\n\n"
            "👆 Нажми на ключ, чтобы скопировать, затем вставь в приложение"
        ),
        parse_mode="HTML",
        reply_markup=_instructions_kb(),
    )
    await callback.answer()


# ─── обратная совместимость ──────────────────────────────────────────────────

@router.callback_query(F.data == "profile_refresh")
async def profile_refresh_legacy(callback: CallbackQuery, session: AsyncSession) -> None:
    await refresh_subscription(callback, session)


@router.callback_query(F.data == "my_connection")
async def my_connection_legacy(callback: CallbackQuery, session: AsyncSession) -> None:
    await show_link(callback, session)
