"""
/start handler — registration, referral linking, welcome screen.

Меню динамическое:
  • Нет активной подписки → ⚡️ Подключить VPN  (+ 🎁 Пробный период если не использован)
  • Есть активная подписка → 📱 Моя подписка
  • Всегда: 🎧 Поддержка | 👥 Партнёрка | 📚 Инструкции
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.config import settings
from bot.models.user import User

router = Router()
logger = logging.getLogger(__name__)


def main_keyboard(user: User) -> ReplyKeyboardMarkup:
    """Динамическое меню в зависимости от статуса подписки."""
    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    rows: list[list[KeyboardButton]] = []

    if has_sub:
        rows.append([KeyboardButton(text="📱 Моя подписка")])
        rows.append([
            KeyboardButton(text="🎁 Подарить VPN"),
            KeyboardButton(text="👥 Партнёрка"),
        ])
    else:
        rows.append([KeyboardButton(text="⚡️ Подключить VPN")])
        if not user.trial_used:
            rows.append([KeyboardButton(text="🎁 Пробный период")])
        rows.append([KeyboardButton(text="👥 Партнёрка")])

    rows.append([KeyboardButton(text="🎧 Поддержка")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _start_inline(user: User) -> InlineKeyboardMarkup:
    """Inline-кнопки в стартовом сообщении."""
    buttons = []

    # Кнопка мини-приложения — всегда присутствует
    if settings.webapp_url:
        buttons.append([InlineKeyboardButton(
            text="🚀 Открыть приложение",
            web_app=WebAppInfo(url=settings.webapp_url + "/app"),
        )])

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if not has_sub:
        if not user.trial_used:
            buttons.append([InlineKeyboardButton(
                text="🎁 Попробовать бесплатно — 2 дня",
                callback_data="activate_trial",
            )])
        buttons.append([InlineKeyboardButton(
            text="⚡️ Подключить VPN",
            callback_data="show_plans",
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _notify_admin_new_user(bot, user: User) -> None:
    uname = f"@{user.username}" if user.username else "без username"
    try:
        await bot.send_message(
            settings.telegram_admin_id,
            f"👤 <b>Новый пользователь!</b>\n"
            f"Имя: {user.full_name}\n"
            f"Username: {uname}\n"
            f"ID: <code>{user.telegram_id}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Admin notify failed: %s", e)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
) -> None:
    tg_id = message.from_user.id
    full_name = message.from_user.full_name or "друг"

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        user = User(
            telegram_id=tg_id,
            username=message.from_user.username,
            full_name=full_name,
        )

        if command.args and command.args.startswith("ref") and command.args[3:].isdigit():
            referrer_id = int(command.args[3:])
            # referral_count раньше увеличивался и здесь, и повторно при первой
            # оплате — из-за этого цифра "оплативших друзей" была завышена.
            # Единственное место, где он растёт теперь — credit_vested_referrals()
            # в bot/tasks/scheduler.py, после того как реферал платит И
            # переживает 30-дневную выдержку. Здесь только фиксируем, кто кого
            # пригласил (immutable — можно поставить лишь один раз, при первом /start).
            if referrer_id != tg_id:
                user.referrer_id = referrer_id

        session.add(user)
        await session.commit()
        await session.refresh(user)
        await _notify_admin_new_user(message.bot, user)

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if has_sub:
        expires = user.subscription_expires_at
        days_left = (expires - now).days
        greeting = (
            f"⭐ <b>С возвращением в STAR VPN!</b>\n\n"
            f"✅ Подписка активна — осталось <b>{days_left} дн.</b>\n\n"
            "Всё работает. Открой приложение, чтобы управлять устройствами."
        )
    else:
        trial_hint = (
            "\n\n🎁 Тебе доступен <b>бесплатный период на 2 дня</b> — активируй прямо сейчас!"
            if not user.trial_used
            else ""
        )
        greeting = (
            f"⭐ <b>Добро пожаловать в STAR VPN</b>\n\n"
            "Твой личный инструмент для безопасного и свободного доступа в интернет. "
            "Мы используем протоколы нового поколения, которые обеспечивают стабильную связь и полную анонимность.\n\n"
            "С помощью этого бота ты можешь:\n"
            "• Мгновенно подключить свои устройства\n"
            "• Управлять подпиской и устройствами\n"
            "• Дарить подписку друзьям\n\n"
            "Нажми на кнопку ниже, чтобы открыть личный кабинет и активировать защиту."
            f"{trial_hint}"
        )

    await message.answer(
        greeting,
        parse_mode="HTML",
        reply_markup=main_keyboard(user),
    )

    await message.answer(
        "👇",
        reply_markup=_start_inline(user),
    )


@router.message(F.text == "🎧 Поддержка")
async def support_handler(message: Message) -> None:
    await message.answer(
        "🎧 <b>Служба поддержки</b>\n\n"
        "Возникли вопросы? Не работает подключение?\n"
        "Напиши нашему администратору — решим любую проблему.\n\n"
        f"👉 <a href=\"https://t.me/{settings.support_username.lstrip('@')}\">Написать в поддержку</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "refresh_menu")
async def refresh_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Обновить меню (например после активации триала)."""
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user:
        await callback.message.answer(
            "✅ Меню обновлено.",
            reply_markup=main_keyboard(user),
        )
    await callback.answer()


@router.callback_query(F.data == "back:main")
async def back_to_main(callback: CallbackQuery, session: AsyncSession) -> None:
    """Возврат в главное меню из любого inline-экрана."""
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    try:
        await callback.message.delete()
    except Exception:
        pass
    if user:
        await callback.message.answer(
            "🏠 Главное меню",
            reply_markup=main_keyboard(user),
        )
    await callback.answer()
