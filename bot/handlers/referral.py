"""
👥 Партнёрка — реферальная программа на днях подписки.

Механика:
  • За каждые 2 друзей, оформивших платную подписку по твоей ссылке,
    рефереру автоматически начисляется +30 дней к своей подписке.
  • Никакого баланса и вывода — бонус применяется сразу, как только
    накопится нужное количество оплативших рефералов.
"""

import logging
from urllib.parse import quote

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.models.user import User
from bot.utils.bot_media import send_screen
from bot.utils.bot_texts import MenuText, image_for, t
from bot.handlers.payment import REFERRAL_DAYS_BONUS, REFERRAL_MILESTONE_SIZE, REFERRAL_ACHIEVEMENTS

router = Router()
logger = logging.getLogger(__name__)


@router.message(MenuText("btn.referral"))
async def referral_info(message: Message, session: AsyncSession) -> None:
    await send_referral_info(message, message.from_user.id, session)


async def send_referral_info(message: Message, tg_id: int, session: AsyncSession) -> None:
    """message — куда ответить (у кнопки своего блока это сообщение бота,
    поэтому tg_id передаётся отдельно)."""
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        await message.answer("Сначала отправь /start.")
        return

    total = (await session.execute(
        select(func.count()).where(User.referrer_id == tg_id)
    )).scalar_one()

    paying = user.referral_count or 0
    days_earned = user.extra_days_granted or 0
    left_to_next = REFERRAL_MILESTONE_SIZE - (paying % REFERRAL_MILESTONE_SIZE)
    if left_to_next == REFERRAL_MILESTONE_SIZE:
        left_to_next = 0

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg_id}"
    share_text = t("referral.share_text")

    buttons = [
        [InlineKeyboardButton(
            text=t("btn.share"),
            url=f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}",
        )],
    ]

    next_milestone_line = (
        f"Ещё {left_to_next} — и начислим +{REFERRAL_DAYS_BONUS} дней автоматически."
        if left_to_next
        else f"Следующие +{REFERRAL_DAYS_BONUS} дней — за ещё {REFERRAL_MILESTONE_SIZE} оплативших друзей."
    )

    achievements_lines = []
    for a in REFERRAL_ACHIEVEMENTS:
        if paying >= a["threshold"]:
            achievements_lines.append(f"{a['icon']} {a['title']} ✅")
        else:
            achievements_lines.append(
                f"{a['icon']} {a['title']} — ещё {a['threshold'] - paying} до +{a['bonus_days']} дней"
            )
    achievements_block = "\n".join(achievements_lines)

    await send_screen(
        message,
        t(
            "referral.text",
            milestone_size=REFERRAL_MILESTONE_SIZE, bonus_days=REFERRAL_DAYS_BONUS,
            invited=total, paying=paying, days_earned=days_earned,
            next_milestone=next_milestone_line, achievements=achievements_block,
            ref_link=ref_link,
        ),
        image=image_for("referral.text"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )
