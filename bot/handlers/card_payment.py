"""
💳 Оплата банковской картой (рубли) через Robokassa.

Тарифы (RUB):
  1 месяц  —  199 ₽
  3 месяца —  499 ₽  (скидка 16%)
  6 месяцев—  899 ₽  (скидка 25%)

Флоу:
  sub:card          → список тарифов
  card:pay:{plan}   → создаём Payment(pending) → строим подписанную
                       ссылку на Robokassa → отправляем пользователю
  POST /card/webhook (api.py) → проверяем подпись ResultURL →
                       выдаём подписку → уведомляем
"""

import logging

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.robokassa import robokassa, CARD_PLANS, payment_inv_id
from bot.utils.database import AsyncSessionLocal

router = Router()
logger = logging.getLogger(__name__)


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def _card_plans_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{plan['label']} — {plan['rub']} ₽",
            callback_data=f"card:pay:{key}",
        )]
        for key, plan in CARD_PLANS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sub:pay_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Handlers ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sub:card")
async def show_card_plans(callback: CallbackQuery) -> None:
    """Показывает тарифы с ценами в рублях."""
    await callback.message.edit_text(
        "💳 <b>Оплата банковской картой</b>\n\n"
        "Visa · Mastercard · МИР — через Robokassa.\n\n"
        "Выбери тариф:",
        parse_mode="HTML",
        reply_markup=_card_plans_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("card:pay:"))
async def card_pay(callback: CallbackQuery) -> None:
    """Создаёт pending-платёж и отправляет пользователю подписанную ссылку Robokassa."""
    plan_key = callback.data.split(":", 2)[2]
    plan = CARD_PLANS.get(plan_key)
    if not plan:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    tg_id = callback.from_user.id
    await callback.answer("⏳ Создаём счёт...")

    async with AsyncSessionLocal() as session:
        # Robokassa требует InvId — целое число, используем id самого платежа.
        payment = Payment(
            order_id="",
            telegram_id=tg_id,
            amount=float(plan["rub"]),
            status="pending",
            payment_method="card",
            days=plan["days"],
        )
        session.add(payment)
        await session.flush()  # присваивает payment.id без коммита
        payment.order_id = f"card_{payment.id}"

        try:
            pay_url = robokassa.build_payment_url(
                inv_id=payment_inv_id(payment.id),
                amount=plan["rub"],
                description=f"STAR VPN - {plan['label']}",
            )
        except RuntimeError as e:
            await session.rollback()
            logger.error("Robokassa build_payment_url failed: %s", e)
            await callback.message.answer(
                "❌ Оплата картой временно недоступна. Попробуй ⭐ Stars."
            )
            return

        await session.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {plan['rub']} ₽", url=pay_url)],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="sub:card")],
    ])

    await callback.message.answer(
        f"💳 <b>Счёт создан!</b>\n\n"
        f"📦 Тариф: <b>{plan['label']}</b>\n"
        f"💵 Сумма: <b>{plan['rub']} ₽</b>\n\n"
        f"Нажми кнопку и оплати картой на защищённой странице Robokassa.\n"
        f"Подписка активируется <b>автоматически</b> после оплаты ✅",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ─── Вызывается из api.py после подтверждения подписи ResultURL ─────────────

async def handle_card_webhook(payment_id: int, bot: Bot) -> None:
    """
    Вызывается из /card/webhook после верификации подписи Robokassa.
    """
    from datetime import datetime
    from bot.handlers.payment import _grant_subscription

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.payment_method == "card",
                Payment.status == "pending",
            )
        )
        payment: Payment | None = result.scalar_one_or_none()

        if not payment:
            logger.warning("Card webhook: pending payment not found for id=%s", payment_id)
            return

        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        days = payment.days or 30

        user_result = await session.execute(
            select(User).where(User.telegram_id == payment.telegram_id)
        )
        user: User | None = user_result.scalar_one_or_none()
        if not user:
            logger.error("Card webhook: user %s not found", payment.telegram_id)
            await session.commit()
            return

        await _grant_subscription(user, days, session)

        plan_label = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}.get(days, f"{days} дней")
        try:
            await bot.send_message(
                payment.telegram_id,
                f"✅ <b>Оплата получена!</b>\n\n"
                f"💳 {float(payment.amount):.0f} ₽\n"
                f"📦 Тариф: <b>{plan_label}</b>\n\n"
                f"Твой STAR VPN активирован 🚀\n"
                f"Перейди в раздел <b>📱 Устройства</b>, чтобы получить ключ.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to notify user %s: %s", payment.telegram_id, e)

    logger.info(
        "Card payment confirmed: id=%s tg=%s rub=%s days=%s",
        payment_id, payment.telegram_id, payment.amount, days,
    )
