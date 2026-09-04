"""
👥 Партнёрка — реферальная программа на днях подписки.

Механика:
  • Друг оплачивает подписку по твоей ссылке и остаётся активным
    REFERRAL_VESTING_DAYS дней (защита от возвратов/чарджбэков) —
    тебе автоматически начисляется REFERRAL_DAYS_PER_REFERRAL дней.
  • Лимит — REFERRAL_MONTHLY_CAP_DAYS дней за скользящие 30 дней.
  • Никакого баланса и вывода — бонус применяется сразу к подписке.
  • Достижения (REFERRAL_ACHIEVEMENTS) — статусы за общее число оплативших
    друзей, без дополнительных дней.
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
from bot.handlers.payment import (
    REFERRAL_DAYS_PER_REFERRAL,
    REFERRAL_VESTING_DAYS,
    REFERRAL_MONTHLY_CAP_DAYS,
    REFERRAL_ACHIEVEMENTS,
)

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

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg_id}"
    share_text = "Попробуй STAR VPN — быстрый и невидимый VPN! 🛡"

    buttons = [
        [InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            url=f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}",
        )],
    ]

    achievements_lines = []
    for a in REFERRAL_ACHIEVEMENTS:
        if paying >= a["threshold"]:
            achievements_lines.append(f"{a['icon']} {a['title']} ✅")
        else:
            achievements_lines.append(f"{a['icon']} {a['title']} — от {a['threshold']} друзей")
    achievements_block = "\n".join(achievements_lines)

    await message.answer(
        f"👥 <b>Партнёрская программа STAR VPN</b>\n\n"
        f"<b>Как работает:</b>\n"
        f"Делись ссылкой → друг оплачивает подписку → остаётся активным "
        f"{REFERRAL_VESTING_DAYS} дней (это защита от возвратов) → тебе автоматически "
        f"начисляется <b>+{REFERRAL_DAYS_PER_REFERRAL} дней</b> за каждого такого друга. "
        f"Лимит — {REFERRAL_MONTHLY_CAP_DAYS} дней в месяц. Никакого вывода — только дни к подписке.\n\n"
        f"📈 <b>Твоя статистика:</b>\n"
        f"👤 Приглашено: <b>{total}</b> чел.\n"
        f"✅ Оплатили и остались: <b>{paying}</b> чел.\n"
        f"🎁 Всего получено дней: <b>{days_earned}</b>\n\n"
        f"🏆 <b>Статусы:</b>\n"
        f"{achievements_block}\n\n"
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )
