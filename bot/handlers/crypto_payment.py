"""
💎 Оплата криптовалютой через @CryptoBot (Crypto Pay API).

Тарифы (USD, принимает USDT / TON / BTC / ETH):
  1 месяц  — $1.50
  3 месяца — $3.99
  6 месяцев— $6.99

Флоу:
  sub:crypto         → список тарифов
  crypto:pay:{plan}  → создаём инвойс → сохраняем в БД → отправляем ссылку
  POST /crypto/webhook (api.py) → выдаём подписку → уведомляем
"""

import logging

from aiogram import Bot, Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select, update

from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
from bot.utils.database import AsyncSessionLocal
from bot.handlers.start import main_keyboard

router = Router()
logger = logging.getLogger(__name__)


# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def _crypto_plans_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{plan['label']} — ${plan['usd']}",
            callback_data=f"crypto:pay:{key}",
        )]
        for key, plan in CRYPTO_PLANS.items()
    ]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="sub:pay_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Handlers ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "sub:crypto")
async def show_crypto_plans(callback: CallbackQuery) -> None:
    """Показывает тарифы с ценами в USD."""
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        if not await is_provider_enabled(session, "crypto"):
            await callback.answer("Оплата криптовалютой сейчас недоступна", show_alert=True)
            return
    await callback.message.edit_text(
        "💎 <b>Оплата криптовалютой</b>\n\n"
        "Принимаем: USDT · TON · BTC · ETH\n"
        "Счёт выставляется через @CryptoBot — безопасно и мгновенно.\n\n"
        "Выбери тариф:",
        parse_mode="HTML",
        reply_markup=_crypto_plans_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crypto:pay:"))
async def crypto_pay(callback: CallbackQuery) -> None:
    """Создаёт инвойс в CryptoPay и отправляет ссылку пользователю."""
    plan_key = callback.data.split(":", 2)[2]
    plan = CRYPTO_PLANS.get(plan_key)
    if not plan:
        await callback.answer("Неизвестный тариф", show_alert=True)
        return

    tg_id = callback.from_user.id

    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        if not await is_provider_enabled(session, "crypto"):
            await callback.answer("Оплата криптовалютой сейчас недоступна", show_alert=True)
            return

    await callback.answer("⏳ Создаём счёт...")

    try:
        payload_str = f"{plan_key}:{tg_id}"
        invoice = await cryptopay.create_invoice(
            usd_amount=plan["usd"],
            payload=payload_str,
            description=f"STAR VPN — {plan['label']}",
        )
    except Exception as e:
        logger.error("CryptoPay create invoice failed for tg=%s: %s", tg_id, e)
        await callback.message.answer(
            "❌ Не удалось создать счёт.\n"
            "Возможно, CryptoPay недоступен — попробуй чуть позже или оплати ⭐ Stars."
        )
        return

    invoice_id = invoice.get("invoice_id")
    pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url", "")

    # Сохраняем pending-платёж в БД
    async with AsyncSessionLocal() as session:
        payment = Payment(
            order_id=f"crypto_{invoice_id}",
            telegram_id=tg_id,
            amount=float(plan["usd"]),
            status="pending",
            payment_method="crypto",
            invoice_id=invoice_id,
            days=plan["days"],
        )
        session.add(payment)
        await session.commit()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💎 Оплатить ${plan['usd']} через @CryptoBot",
            url=pay_url,
        )],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="sub:crypto")],
    ])

    await callback.message.answer(
        f"💎 <b>Счёт создан!</b>\n\n"
        f"📦 Тариф: <b>{plan['label']}</b>\n"
        f"💵 Сумма: <b>${plan['usd']}</b>\n"
        f"Валюты: USDT · TON · BTC · ETH\n\n"
        f"Нажми кнопку и оплати через @CryptoBot.\n"
        f"Подписка активируется <b>автоматически</b> после оплаты ✅\n\n"
        f"⏱ Счёт действителен 1 час.",
        parse_mode="HTML",
        reply_markup=kb,
    )


# ─── Вызывается из api.py после подтверждения webhook ────────────────────────

async def handle_crypto_webhook(
    invoice_id: int,
    asset: str,
    bot: Bot,
    invoice_payload: str = "",
) -> None:
    """
    Вызывается из /crypto/webhook после верификации подписи.
    Поддерживает обычные платежи и подарки (payload начинается с 'gift:').

    Отметка об оплате и выдача подписки — одна транзакция (единственный
    коммит внутри _grant_subscription): если выдача упала, откатывается и
    отметка, исключение уходит в api.py, и вебхук можно доставить повторно.
    Повторная доставка после успеха ничего не делает — pending-строки нет.
    """
    from datetime import datetime
    from bot.handlers.card_payment import _notify_gift_recipient
    from bot.handlers.payment import _credit_referral, _grant_subscription

    is_gift = invoice_payload.startswith("gift:")

    async with AsyncSessionLocal() as session:
        claimed = await session.execute(
            update(Payment)
            .where(
                Payment.invoice_id == invoice_id,
                Payment.payment_method == "crypto",
                Payment.status == "pending",
            )
            .values(status="paid", asset=asset, paid_at=datetime.utcnow())
            .returning(Payment.id)
        )
        payment_id = claimed.scalar_one_or_none()
        if payment_id is None:
            await session.rollback()
            logger.warning("Crypto webhook: no pending payment for invoice_id=%s", invoice_id)
            return
        payment = await session.get(Payment, payment_id)
        days = payment.days or 30
        plan_label = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}.get(days, f"{days} дней")

        if is_gift:
            # Формат payload: gift:{plan_key}:{recipient_id}:{anon}:{sender_id}
            parts = invoice_payload.split(":")
            recipient_id = int(parts[2]) if len(parts) > 2 else payment.telegram_id
            anon = parts[3] == "1" if len(parts) > 3 else False
            sender_id = int(parts[4]) if len(parts) > 4 else payment.telegram_id
            # Счета, выставленные до появления этих полей, заполняем из payload —
            # от них зависят имя дарителя и запись о подарке.
            payment.is_gift = True
            if payment.gift_sender_id is None:
                payment.gift_sender_id = sender_id
                payment.gift_anon = anon

            recipient_result = await session.execute(
                select(User).where(User.telegram_id == recipient_id)
            )
            recipient: User | None = recipient_result.scalar_one_or_none()
            if not recipient:
                logger.error("Crypto gift: recipient %s not found", recipient_id)
                await session.commit()
                return

            await _grant_subscription(recipient, days, session)  # коммитит и отметку
            # Уведомление получателю (Telegram + окно о подарке в мини-аппе/
            # кабинете) и личное сообщение — как у подарков Stars и картой.
            await _notify_gift_recipient(payment, recipient, plan_label, bot, session)

            sender = await session.get(User, sender_id)
            try:
                await bot.send_message(
                    sender_id,
                    f"✅ <b>Подарок отправлен!</b>\n\n"
                    f"💎 {asset} · ${float(payment.amount):.2f}\n"
                    f"📦 Тариф: <b>{plan_label}</b>\n"
                    f"Получатель уже может пользоваться VPN 🎉",
                    parse_mode="HTML",
                    reply_markup=main_keyboard(sender) if sender else None,
                )
            except Exception as e:
                logger.error("Gift notify sender error: %s", e)

        else:
            # Обычный платёж
            user_result = await session.execute(
                select(User).where(User.telegram_id == payment.telegram_id)
            )
            user: User | None = user_result.scalar_one_or_none()
            if not user:
                logger.error("Crypto webhook: user %s not found", payment.telegram_id)
                await session.commit()
                return

            await _grant_subscription(user, days, session)  # коммитит и отметку
            try:
                await _credit_referral(user, session, bot)
            except Exception:
                logger.exception("Crypto webhook: referral credit failed, invoice=%s", invoice_id)

            try:
                await bot.send_message(
                    payment.telegram_id,
                    f"✅ <b>Оплата получена!</b>\n\n"
                    f"💎 {asset} · ${float(payment.amount):.2f}\n"
                    f"📦 Тариф: <b>{plan_label}</b>\n\n"
                    f"Твой STAR VPN активирован 🚀\n"
                    f"Перейди в раздел <b>📱 Устройства</b>, чтобы получить ключ.",
                    parse_mode="HTML",
                    reply_markup=main_keyboard(user),
                )
            except Exception as e:
                logger.error("Failed to notify user %s: %s", payment.telegram_id, e)

    logger.info(
        "Crypto %s confirmed: invoice_id=%s tg=%s $%s days=%s asset=%s",
        "gift" if is_gift else "payment",
        invoice_id, payment.telegram_id, payment.amount, days, asset,
    )
