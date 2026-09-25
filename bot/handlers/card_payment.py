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

import html
import logging
import uuid

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.robokassa import robokassa, CARD_PLANS, payment_inv_id
from bot.utils.database import AsyncSessionLocal
from bot.handlers.start import main_keyboard

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
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        if not await is_provider_enabled(session, "card"):
            await callback.answer("Оплата картой сейчас недоступна", show_alert=True)
            return
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

    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        if not await is_provider_enabled(session, "card"):
            await callback.answer("Оплата картой сейчас недоступна", show_alert=True)
            return

    await callback.answer("⏳ Создаём счёт...")

    async with AsyncSessionLocal() as session:
        # Robokassa требует InvId — целое число, используем id самого платежа,
        # который узнаём только после flush ниже. До этого момента order_id
        # должен быть чем-то временным, но ГАРАНТИРОВАННО уникальным (колонка
        # unique=True) — раньше здесь была одна и та же "" для всех, и два
        # одновременных запроса на оплату картой падали с IntegrityError.
        payment = Payment(
            order_id=f"card_pending_{uuid.uuid4().hex}",
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

async def handle_card_webhook(payment_id: int, bot: Bot, out_sum: str | None = None) -> None:
    """
    Вызывается из /card/webhook после верификации подписи Robokassa.
    Robokassa повторяет ResultURL, пока не получит OK, — поэтому платёж
    помечается оплаченным атомарно (UPDATE … WHERE status='pending'), и
    повтор не выдаёт подписку второй раз.
    """
    from datetime import datetime
    from bot.handlers.payment import _credit_referral, _grant_subscription

    async with AsyncSessionLocal() as session:
        payment = await session.get(Payment, payment_id)
        if not payment or payment.payment_method != "card":
            logger.warning("Card webhook: payment not found for id=%s", payment_id)
            return
        if out_sum is not None and abs(float(out_sum) - float(payment.amount)) > 0.01:
            logger.error("Card webhook: amount mismatch for id=%s (paid %s, expected %s)",
                         payment_id, out_sum, payment.amount)
            return

        claimed = await session.execute(
            update(Payment)
            .where(Payment.id == payment_id, Payment.status == "pending")
            .values(status="paid", paid_at=datetime.utcnow())
        )
        await session.commit()
        if claimed.rowcount != 1:
            logger.info("Card webhook: payment id=%s already processed", payment_id)
            return
        await session.refresh(payment)
        days = payment.days or 30

        if payment.gift_link_code:
            # Подарок по ссылке — получатель ещё не известен, ничего не
            # выдаём сейчас. Подписка достанется тому, кто заберёт по
            # /gift/{code} (см. POST /api/gift/link/{code}/claim в api.py).
            await session.commit()
            logger.info(
                "Card gift-link payment confirmed: id=%s code=%s rub=%s days=%s",
                payment_id, payment.gift_link_code, payment.amount, days,
            )
            return

        user_result = await session.execute(
            select(User).where(User.telegram_id == payment.telegram_id)
        )
        user: User | None = user_result.scalar_one_or_none()
        if not user:
            logger.error("Card webhook: user %s not found", payment.telegram_id)
            await session.commit()
            return

        await _grant_subscription(user, days, session)
        if not payment.is_gift:
            # Первая оплата друга по реферальной ссылке — бонус рефереру
            # (раньше засчитывались только оплаты звёздами).
            await _credit_referral(user, session, bot)

        plan_label = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}.get(days, f"{days} дней")

        if payment.is_gift:
            await _notify_gift_recipient(payment, user, plan_label, bot, session)
        else:
            try:
                await bot.send_message(
                    payment.telegram_id,
                    f"✅ <b>Оплата получена!</b>\n\n"
                    f"💳 {float(payment.amount):.0f} ₽\n"
                    f"📦 Тариф: <b>{plan_label}</b>\n\n"
                    f"Твой STAR VPN активирован 🚀\n"
                    f"Перейди в раздел <b>📱 Устройства</b>, чтобы получить ключ.",
                    parse_mode="HTML",
                    reply_markup=main_keyboard(user),
                )
            except Exception as e:
                logger.error("Failed to notify user %s: %s", payment.telegram_id, e)

    logger.info(
        "Card payment confirmed: id=%s tg=%s rub=%s days=%s gift=%s",
        payment_id, payment.telegram_id, payment.amount, days, payment.is_gift,
    )


async def _notify_gift_recipient(
    payment: Payment, recipient: User, plan_label: str, bot: Bot, session: AsyncSession
) -> None:
    """Общая логика уведомления о сайтовом подарке (картой) — GiftNotification
    для мини-аппа + сообщение в Telegram получателю с учётом анонимности."""
    from bot.models.gift_notification import GiftNotification
    from bot.handlers.gift import _instructions_kb

    sender_name = "Аноним 🕵️"
    if not payment.gift_anon and payment.gift_sender_id:
        sender_result = await session.execute(
            select(User).where(User.telegram_id == payment.gift_sender_id)
        )
        sender: User | None = sender_result.scalar_one_or_none()
        if sender:
            sender_name = f"@{sender.username}" if sender.username else (sender.full_name or sender.email or "пользователь")

    notif = GiftNotification(
        recipient_id=recipient.telegram_id,
        sender_name=sender_name,
        plan_label=plan_label,
        plan_days=payment.days or 30,
    )
    session.add(notif)
    await session.commit()

    exp_str = recipient.subscription_expires_at.strftime("%d.%m.%Y") if recipient.subscription_expires_at else "—"
    personal_block = f"\n\n💬 <i>«{html.escape(payment.gift_message)}»</i>" if payment.gift_message else ""

    notif_text = (
        f"🎁 <b>Тебе подарили подписку STAR VPN!</b>\n\n"
        f"От: <b>{html.escape(sender_name)}</b>\n"
        f"📦 Тариф: <b>{plan_label}</b>\n"
        f"⏳ Действует до: <b>{exp_str}</b>"
        f"{personal_block}\n\n"
        f"Нажми <b>📱 Моя подписка</b> чтобы подключиться."
    )
    try:
        await bot.send_message(
            recipient.telegram_id, notif_text, parse_mode="HTML",
            message_effect_id="5046509860389126442", reply_markup=_instructions_kb(),
        )
    except Exception:
        try:
            await bot.send_message(
                recipient.telegram_id, notif_text, parse_mode="HTML",
                reply_markup=_instructions_kb(),
            )
        except Exception as e:
            logger.warning("Could not notify gift recipient %s: %s", recipient.telegram_id, e)
