"""
👥 Партнёрка — реферальная программа со Stars.

Механика:
  • 10% от каждой покупки реферала → Stars на баланс реферера
  • Минимум для вывода: 100 ⭐
  • Вывод: пользователь создаёт заявку → админ одобряет/отклоняет
  • При одобрении баланс списывается, Stars выплачиваются вручную через Fragment
"""

import logging
from urllib.parse import quote

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.config import settings
from bot.models.user import User
from bot.models.withdrawal import WithdrawalRequest

TOP_SIZE = 5

router = Router()
logger = logging.getLogger(__name__)

WITHDRAWAL_MIN = 100  # минимум Stars для подачи заявки


# ─────────────────────────────── главная ────────────────────────────────────

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

    paying = (await session.execute(
        select(func.count()).where(
            User.referrer_id == tg_id,
            User.subscription_expires_at.isnot(None),
        )
    )).scalar_one()

    balance = user.referral_stars_balance or 0

    # Есть ли уже активная pending-заявка?
    pending_req = (await session.execute(
        select(WithdrawalRequest).where(
            WithdrawalRequest.telegram_id == tg_id,
            WithdrawalRequest.status == "pending",
        )
    )).scalar_one_or_none()

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref{tg_id}"
    share_text = "Попробуй STAR VPN — быстрый и невидимый VPN! 🛡"

    buttons = [
        [InlineKeyboardButton(
            text="📤 Поделиться ссылкой",
            url=f"https://t.me/share/url?url={quote(ref_link)}&text={quote(share_text)}",
        )],
    ]

    if pending_req:
        buttons.append([InlineKeyboardButton(
            text="⏳ Заявка на вывод ожидает рассмотрения",
            callback_data="ref:withdrawal_status",
        )])
    elif balance >= WITHDRAWAL_MIN:
        buttons.append([InlineKeyboardButton(
            text=f"💸 Вывести {balance} ⭐",
            callback_data="ref:withdraw",
        )])

    await message.answer(
        f"👥 <b>Партнёрская программа STAR VPN</b>\n\n"
        f"<b>Как работает:</b>\n"
        f"Делись ссылкой → друг покупает подписку → "
        f"ты получаешь <b>10% от суммы покупки</b> в Stars на баланс.\n\n"
        f"💰 <b>Вывод Stars:</b>\n"
        f"Минимум <b>{WITHDRAWAL_MIN} ⭐</b> для подачи заявки.\n"
        f"Заявки обрабатываются в течение <b>24 часов</b>.\n"
        f"Stars переводятся на твой аккаунт Telegram.\n\n"
        f"📈 <b>Твоя статистика:</b>\n"
        f"👤 Приглашено: <b>{total}</b> чел.\n"
        f"✅ Оплатили подписку: <b>{paying}</b> чел.\n"
        f"⭐ Партнёрский баланс: <b>{balance} ⭐</b>\n\n"
        f"🔗 <b>Твоя реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        disable_web_page_preview=True,
    )


# ─────────────────────────────── вывод Stars ────────────────────────────────

@router.callback_query(F.data == "ref:withdraw")
async def withdraw_request(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    balance = user.referral_stars_balance or 0
    if balance < WITHDRAWAL_MIN:
        await callback.answer(
            f"Минимум {WITHDRAWAL_MIN} ⭐. У тебя {balance} ⭐.",
            show_alert=True,
        )
        return

    # Проверить нет ли уже pending заявки
    existing = (await session.execute(
        select(WithdrawalRequest).where(
            WithdrawalRequest.telegram_id == tg_id,
            WithdrawalRequest.status == "pending",
        )
    )).scalar_one_or_none()

    if existing:
        await callback.answer("У тебя уже есть активная заявка на вывод.", show_alert=True)
        return

    await callback.message.answer(
        f"💸 <b>Подтверди заявку на вывод</b>\n\n"
        f"Сумма: <b>{balance} ⭐</b>\n"
        f"Stars поступят на твой аккаунт Telegram в течение <b>24 часов</b>.\n\n"
        f"Подтверждаешь?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="ref:confirm_withdraw"),
                InlineKeyboardButton(text="❌ Отмена",      callback_data="ref:cancel_withdraw"),
            ]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "ref:confirm_withdraw")
async def confirm_withdraw(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user or (user.referral_stars_balance or 0) < WITHDRAWAL_MIN:
        await callback.answer("Недостаточно Stars.", show_alert=True)
        return

    balance = user.referral_stars_balance

    # Создаём заявку (баланс списывается сразу — при отклонении возвращается)
    req = WithdrawalRequest(
        telegram_id=tg_id,
        stars_amount=balance,
        status="pending",
    )
    session.add(req)
    user.referral_stars_balance = 0
    await session.commit()
    await session.refresh(req)

    await callback.message.edit_text(
        f"✅ <b>Заявка #{req.id} создана!</b>\n\n"
        f"Сумма: <b>{balance} ⭐</b>\n"
        f"Статус: ⏳ На рассмотрении\n\n"
        f"Мы уведомим тебя, когда Stars будут переведены.",
        parse_mode="HTML",
    )
    await callback.answer("Заявка отправлена!")

    # Уведомить админа
    uname = f"@{user.username}" if user.username else str(tg_id)
    try:
        await callback.bot.send_message(
            settings.telegram_admin_id,
            f"💸 <b>Запрос на вывод Stars!</b>\n\n"
            f"Пользователь: {uname} (<code>{tg_id}</code>)\n"
            f"Сумма: <b>{balance} ⭐</b>\n"
            f"Заявка #{req.id}\n\n"
            f"После перевода Stars через Fragment нажми «Подтвердить».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Подтвердить выплату",
                        callback_data=f"adm:wd_approve:{req.id}",
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"adm:wd_reject:{req.id}",
                    ),
                ]
            ]),
        )
    except Exception as e:
        logger.warning("Failed to notify admin about withdrawal: %s", e)


@router.callback_query(F.data == "ref:cancel_withdraw")
async def cancel_withdraw(callback: CallbackQuery) -> None:
    await callback.message.edit_text("❌ Заявка отменена.")
    await callback.answer()


@router.callback_query(F.data == "ref:withdrawal_status")
async def withdrawal_status(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    req = (await session.execute(
        select(WithdrawalRequest).where(
            WithdrawalRequest.telegram_id == tg_id,
            WithdrawalRequest.status == "pending",
        )
    )).scalar_one_or_none()

    if req:
        await callback.answer(
            f"Заявка #{req.id} на вывод {req.stars_amount} ⭐ ожидает обработки (до 24ч).",
            show_alert=True,
        )
    else:
        await callback.answer("Активных заявок нет.", show_alert=True)
