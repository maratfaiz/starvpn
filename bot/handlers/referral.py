"""
👥 Партнёрка — реферальная программа на днях подписки.

Механика (с 2026-08-31, см. ADR-016 в AGENTS/decisions/ADR.md):
  • Приглашённый друг получает +REFEREE_BONUS_DAYS дней сразу при первой
    оплате подписки по твоей ссылке.
  • Пригласивший получает дни только за достижения (REFERRAL_ACHIEVEMENTS,
    разово на порогах 2/5/10/25 оплативших друзей) — никакой отдельной
    "пачки за каждые N друзей" больше нет.
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
from bot.handlers.payment import REFEREE_BONUS_DAYS, REFERRAL_ACHIEVEMENTS

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

    next_achievement = next((a for a in REFERRAL_ACHIEVEMENTS if a["threshold"] > paying), None)
    next_milestone_line = (
        f"Ещё {next_achievement['threshold'] - paying} — и получишь +{next_achievement['bonus_days']} дней "
        f"(«{next_achievement['title']}»).\n\n"
        if next_achievement
        else "Все достижения уже открыты — ты в топе партнёров STAR VPN! 🎉\n\n"
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
        f"Делись ссылкой → друг покупает подписку → он сразу получает "
        f"<b>+{REFEREE_BONUS_DAYS} дня</b>, а тебе открываются достижения ниже "
        f"по мере роста числа оплативших друзей. "
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
