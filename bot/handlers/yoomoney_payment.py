"""
🟣 Оплата через ЮMoney (карта / СБП / кошелёк) — второй рублёвый рельс,
резерв на случай проблем с Robokassa. Те же тарифы, что и у карты.

Флоу:
  sub:yoomoney          → список тарифов
  yoomoney:pay:{plan}   → создаём Payment(pending) → строим ссылку Quickpay
                          → отправляем пользователю
  POST /yoomoney/webhook (api.py) → проверяем подпись уведомления →
                          выдаём подписку → уведомляем
"""

import logging

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.yoomoney import yoomoney, CARD_PLANS, payment_label
from bot.utils.database import AsyncSessionLocal

router = Router()
logger = logging.getLogger(__name__)


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def _yoomoney_plans_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{plan['label']} — {plan['rub']} ₽",
            callback_data=f"yoomoney:pay:{key}",
        )]
        for key, plan in CARD_PLANS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sub:pay_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Handlers ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sub:yoomoney")
async def show_yoomoney_plans(callback: CallbackQuery) -> None:
    """Показывает тарифы с ценами в рублях."""
    await callback.message.edit_text(
        "🟣 <b>Оплата через ЮMoney</b>\n\n"
        "Карта, СБП или кошелёк ЮMoney — паспорт не нужен.\n\n"
        "Выбери тариф:",
        parse_mode="HTML",
        reply_markup=_yoomoney_plans_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("yoomoney:pay:"))
async def yoomoney_pay(callback: CallbackQuery) -> None:
    """Создаёт pending-платёж и отправляет пользователю ссылку Quickpay."""
    plan_key = callback.data.split(":", 2)[2]
    plan = CARD_PLANS.get(plan_key)
    if not plan:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    tg_id = callback.from_user.id
    await callback.answer("⏳ Создаём счёт...")

    async with AsyncSessionLocal() as session:
        payment = Payment(
            order_id="",
            telegram_id=tg_id,
            amount=float(plan["rub"]),
            status="pending",
            payment_method="yoomoney",
            days=plan["days"],
        )
        session.add(payment)
        await session.flush()  # присваивает payment.id без коммита
        payment.order_id = f"yoomoney_{payment.id}"

        try:
            pay_url = yoomoney.build_payment_url(
                label=payment_label(payment.id),
                amount=plan["rub"],
                description=f"STAR VPN - {plan['label']}",
            )
        except RuntimeError as e:
            await session.rollback()
            logger.error("YooMoney build_payment_url failed: %s", e)
            await callback.message.answer(
                "❌ Оплата через ЮMoney временно недоступна. Попробуй ⭐ Stars или 💳 карту."
            )
            return

        await session.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🟣 Оплатить {plan['rub']} ₽", url=pay_url)],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="sub:yoomoney")],
    ])

    await callback.message.answer(
        f"🟣 <b>Счёт создан!</b>\n\n"
        f"📦 Тариф: <b>{plan['label']}</b>\n"
        f"💵 Сумма: <b>{plan['rub']} ₽</b>\n\n"
        f"Нажми кнопку и оплати картой, через СБП или из кошелька ЮMoney.\n"
        f"Подписка активируется <b>автоматически</b> после оплаты ✅",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ─── Вызывается из api.py после подтверждения подписи уведомления ───────────

async def handle_yoomoney_webhook(payment_id: int, bot: Bot) -> None:
    """
    Вызывается из /yoomoney/webhook после верификации подписи ЮMoney.
    """
    from datetime import datetime
    from bot.handlers.payment import _grant_subscription

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.payment_method == "yoomoney",
                Payment.status == "pending",
            )
        )
        payment: Payment | None = result.scalar_one_or_none()

        if not payment:
            logger.warning("YooMoney webhook: pending payment not found for id=%s", payment_id)
            return

        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        days = payment.days or 30

        user_result = await session.execute(
            select(User).where(User.telegram_id == payment.telegram_id)
        )
        user: User | None = user_result.scalar_one_or_none()
        if not user:
            logger.error("YooMoney webhook: user %s not found", payment.telegram_id)
            await session.commit()
            return

        await _grant_subscription(user, days, session)

        plan_label = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}.get(days, f"{days} дней")
        try:
            await bot.send_message(
                payment.telegram_id,
                f"✅ <b>Оплата получена!</b>\n\n"
                f"🟣 {float(payment.amount):.0f} ₽ через ЮMoney\n"
                f"📦 Тариф: <b>{plan_label}</b>\n\n"
                f"Твой STAR VPN активирован 🚀\n"
                f"Перейди в раздел <b>📱 Устройства</b>, чтобы получить ключ.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error("Failed to notify user %s: %s", payment.telegram_id, e)

    logger.info(
        "YooMoney payment confirmed: id=%s tg=%s rub=%s days=%s",
        payment_id, payment.telegram_id, payment.amount, days,
    )
