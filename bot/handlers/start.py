"""
/start handler — registration, referral linking, welcome screen.

Меню динамическое:
  • Нет активной подписки → ⚡️ Подключить VPN  (+ 🎁 Пробный период если не использован)
  • Есть активная подписка → 📱 Моя подписка
  • Всегда: 🎧 Поддержка | 👥 Партнёрка | 📚 Инструкции
"""

import html
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
from bot.utils.bot_media import send_screen
from bot.utils.bot_texts import MenuText, image_for, t

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
            f"Имя: {html.escape(user.full_name or '')}\n"
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
            # referral_count — число ОПЛАТИВШИХ друзей (его увеличивает только
            # _credit_referral при первой оплате). Раньше он рос уже здесь, на
            # /start, и бонус «за 2 оплативших» выдавался за одного.
            if referrer_id != tg_id and await session.get(User, referrer_id):
                user.referrer_id = referrer_id

        session.add(user)
        await session.commit()
        await session.refresh(user)
        await _notify_admin_new_user(message.bot, user)

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if has_sub:
        days_left = (user.subscription_expires_at - now).days
        greeting_key = "start.welcome_back"
        greeting = t(greeting_key, days_left=days_left)
    else:
        greeting_key = "start.welcome_new"
        greeting = t(greeting_key)
        if not user.trial_used:
            greeting += "\n\n" + t("start.trial_hint")

    await send_screen(
        message, greeting, image=image_for(greeting_key), reply_markup=main_keyboard(user),
    )

    await message.answer(
        t("start.inline_prompt"),
        reply_markup=_start_inline(user),
    )


def support_text() -> str:
    return t("support.text", support_link=f"https://t.me/{settings.support_username.lstrip('@')}")


@router.message(MenuText("btn.support"))
async def support_handler(message: Message) -> None:
    await send_screen(
        message, support_text(), image=image_for("support.text"), disable_web_page_preview=True,
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
        await send_screen(
            callback.message, t("menu.title"), image=image_for("menu.title"),
            reply_markup=main_keyboard(user),
        )
    await callback.answer()
