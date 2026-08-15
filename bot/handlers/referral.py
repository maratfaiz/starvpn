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

from aiogram import Router, F
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.models.user import User
from bot.handlers.payment import REFERRAL_DAYS_BONUS, REFERRAL_MILESTONE_SIZE, REFERRAL_ACHIEVEMENTS

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "👥 Партнёрка")
async def referral_info(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id

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
    share_text = "Попробуй STAR VPN — быстрый и невидимый VPN! 🛡"

    buttons = [
        [InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            url=f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}",
        )],
    ]

    next_milestone_line = (
        f"Ещё {left_to_next} — и начислим +{REFERRAL_DAYS_BONUS} дней автоматически.\n\n"
        if left_to_next
        else f"Следующие +{REFERRAL_DAYS_BONUS} дней — за ещё {REFERRAL_MILESTONE_SIZE} оплативших друзей.\n\n"
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

    await message.answer(
        f"👥 <b>Партнёрская программа STAR VPN</b>\n\n"
        f"<b>Как работает:</b>\n"
        f"Делись ссылкой → друг покупает подписку → "
        f"за каждые <b>{REFERRAL_MILESTONE_SIZE} оплативших друзей</b> тебе автоматически "
        f"добавляется <b>+{REFERRAL_DAYS_BONUS} дней</b> к твоей подписке. "
        f"Никакого вывода — бонус применяется сразу.\n\n"
        f"📈 <b>Твоя статистика:</b>\n"
        f"👤 Приглашено: <b>{total}</b> чел.\n"
        f"✅ Оплатили подписку: <b>{paying}</b> чел.\n"
        f"🎁 Всего получено дней: <b>{days_earned}</b>\n\n"
        f"{next_milestone_line}"
        f"🏆 <b>Достижения:</b>\n"
        f"{achievements_block}\n\n"
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )
