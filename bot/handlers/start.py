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
from bot.utils import bot_texts
from bot.utils.bot_texts import MenuText, t

router = Router()
logger = logging.getLogger(__name__)


def main_keyboard(user: User) -> ReplyKeyboardMarkup:
    """Динамическое меню в зависимости от статуса подписки."""
    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    rows: list[list[KeyboardButton]] = []

    def visible(*keys: str) -> list[KeyboardButton]:
        return [KeyboardButton(text=t(k)) for k in keys if not bot_texts.is_hidden(k)]

    if has_sub:
        rows.append(visible("btn.my_sub"))
        rows.append(visible("btn.gift", "btn.referral"))
    else:
        rows.append(visible("btn.connect"))
        if not user.trial_used:
            rows.append(visible("btn.trial"))
        rows.append(visible("btn.referral"))

    # Свои блоки из админки (/admin → Бот), вынесенные в главное меню.
    rows.extend([KeyboardButton(text=b["menu_label"])] for b in bot_texts.menu_blocks())
    rows.append(visible("btn.support"))
    rows = [r for r in rows if r]

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _start_inline(user: User) -> InlineKeyboardMarkup:
    """Inline-кнопки в стартовом сообщении."""
    buttons = []

    # Кнопка мини-приложения — всегда присутствует
    if settings.webapp_url:
        buttons.append([InlineKeyboardButton(
            text=t("btn.open_app"),
            web_app=WebAppInfo(url=settings.webapp_url + "/app"),
        )])

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if not has_sub:
        if not user.trial_used:
            buttons.append([InlineKeyboardButton(
                text=t("btn.try_trial"),
                callback_data="activate_trial",
            )])
        buttons.append([InlineKeyboardButton(
            text=t("btn.connect_inline"),
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
            if referrer_id != tg_id:
                user.referrer_id = referrer_id
                ref_result = await session.execute(
                    select(User).where(User.telegram_id == referrer_id)
                )
                referrer: User | None = ref_result.scalar_one_or_none()
                if referrer:
                    referrer.referral_count = (referrer.referral_count or 0) + 1

        session.add(user)
        await session.commit()
        await session.refresh(user)
        await _notify_admin_new_user(message.bot, user)

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if has_sub:
        days_left = (user.subscription_expires_at - now).days
        greeting = t("start.welcome_back", days_left=days_left)
    else:
        greeting = t("start.welcome_new")
        if not user.trial_used:
            greeting += "\n\n" + t("start.trial_hint")

    await message.answer(
        greeting,
        parse_mode="HTML",
        reply_markup=main_keyboard(user),
    )

    await message.answer(
        t("start.inline_prompt"),
        reply_markup=_start_inline(user),
    )


def support_text() -> str:
    return t("support.text", support_link=f"https://t.me/{settings.support_username.lstrip('@')}")


@router.message(MenuText("btn.support"))
async def support_handler(message: Message) -> None:
    await message.answer(
        support_text(),
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
            t("menu.title"),
            reply_markup=main_keyboard(user),
        )
    await callback.answer()
