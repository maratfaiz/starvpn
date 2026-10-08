"""
Подарки по ссылке — единственный способ подарить подписку (ADR-022).

Даритель выбирает срок, платит (Stars или крипта в боте, крипта на сайте)
и получает ссылку {SITE_URL}/gift/{код} — отправляет её кому угодно.
Получатель открывает ссылку на сайте или в боте (/start gift_{код}) и
забирает подарок под своим аккаунтом. Раньше нужно было знать @username
получателя, и тот должен был заранее запустить бота.

Получатель неизвестен до клейма, поэтому Payment.telegram_id (NOT NULL,
FK) до этого момента указывает на дарителя (ADR-011). Оплата подарка
ничего не выдаёт — подписку выдаёт claim_gift. Подарки, созданные из
админки, — payment_method="admin", сумма 0, даритель — «STAR VPN».

Старые счета на подарок конкретному человеку (payload "gift:…") ещё
обрабатываются по-старому — в bot/handlers/gift.py и crypto_payment.py.
"""

import html
import logging
import secrets
import urllib.parse

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.gift_notification import GiftNotification
from bot.models.payment import Payment
from bot.models.user import User

logger = logging.getLogger(__name__)

GIFT_PLAN_LABELS = {30: "1 месяц", 90: "3 месяца", 180: "6 месяцев"}
LINK_PAYLOAD_PREFIX = "giftlink:"


def plan_label(days: int) -> str:
    return GIFT_PLAN_LABELS.get(days, f"{days} дней")


def new_gift_code() -> str:
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:11]


def gift_url(code: str) -> str:
    return f"{settings.site_url}/gift/{code}"


def gift_bot_url(code: str) -> str:
    return f"https://t.me/{settings.bot_username.lstrip('@')}?start=gift_{code}"


def link_payload(payment_id: int) -> str:
    """Payload счёта (Stars / CryptoPay) для подарка по ссылке."""
    return f"{LINK_PAYLOAD_PREFIX}{payment_id}"


def parse_link_payload(payload: str) -> int | None:
    if not payload.startswith(LINK_PAYLOAD_PREFIX):
        return None
    rest = payload[len(LINK_PAYLOAD_PREFIX):]
    return int(rest) if rest.isdigit() else None


def link_gift_fields(sender_id: int, days: int, anon: bool, message: str) -> dict:
    """Поля pending-платежа подарка по ссылке (до оплаты telegram_id = даритель)."""
    return {
        "telegram_id": sender_id, "days": days, "status": "pending", "is_gift": True,
        "gift_sender_id": sender_id, "gift_anon": anon, "gift_message": message or None,
        "gift_link_code": new_gift_code(),
    }


async def sender_name(payment: Payment, session: AsyncSession) -> str:
    if payment.payment_method == "admin":
        return "STAR VPN"
    if payment.gift_anon or not payment.gift_sender_id:
        return "Аноним"
    sender = await session.get(User, payment.gift_sender_id)
    if not sender:
        return "Аноним"
    return f"@{sender.username}" if sender.username else (sender.full_name or "пользователь")


def _share_kb(code: str) -> InlineKeyboardMarkup:
    share = "https://t.me/share/url?" + urllib.parse.urlencode({
        "url": gift_url(code), "text": "🎁 Дарю тебе подписку STAR VPN — забери по ссылке",
    })
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Отправить другу", url=share)],
        [InlineKeyboardButton(text="🎁 Открыть подарок", url=gift_url(code))],
    ])


async def send_gift_link(bot: Bot, payment: Payment) -> None:
    """Дарителю в Telegram — ссылка на оплаченный подарок."""
    if not payment.gift_sender_id or payment.gift_sender_id <= 0 or not payment.gift_link_code:
        return
    code = payment.gift_link_code
    try:
        await bot.send_message(
            payment.gift_sender_id,
            f"🎁 <b>Подарок оплачен!</b>\n\n"
            f"📦 {plan_label(payment.days or 30)}\n\n"
            f"Отправьте другу эту ссылку — по ней он заберёт подписку:\n"
            f"{gift_url(code)}\n\n"
            f"Или ссылку на бота: {gift_bot_url(code)}\n\n"
            f"Ссылка одноразовая. Все ваши подарки — в личном кабинете на сайте.",
            parse_mode="HTML",
            reply_markup=_share_kb(code),
            disable_web_page_preview=True,
        )
    except Exception as e:  # noqa: BLE001 — даритель мог заблокировать бота; подарок уже оплачен
        logger.warning("Gift link notify failed for sender %s: %s", payment.gift_sender_id, e)


class GiftClaimError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


async def claim_gift(code: str, claimant: User, session: AsyncSession) -> dict:
    """Забрать подарок по коду: атомарно помечает его забранным, выдаёт дни
    (единственный коммит — внутри _grant_subscription, вместе с отметкой) и
    создаёт GiftNotification. Ошибки — GiftClaimError с HTTP-статусом."""
    from bot.handlers.payment import _grant_subscription

    payment = (await session.execute(
        select(Payment).where(Payment.gift_link_code == code, Payment.is_gift.is_(True))
    )).scalar_one_or_none()
    if not payment:
        raise GiftClaimError(404, "Подарок не найден")
    if payment.status != "paid":
        raise GiftClaimError(409, "Даритель ещё не завершил оплату")
    if payment.gift_claimed:
        raise GiftClaimError(409, "Этот подарок уже кто-то забрал")
    if payment.gift_sender_id == claimant.telegram_id and payment.payment_method != "admin":
        raise GiftClaimError(400, "Нельзя забрать свой же подарок — отправьте ссылку другу")
    if claimant.is_banned:
        raise GiftClaimError(403, "Аккаунт заблокирован")

    # Атомарно: при двух одновременных запросах подписку получит только один.
    taken = await session.execute(
        update(Payment)
        .where(Payment.id == payment.id, Payment.gift_claimed.is_(False))
        .values(gift_claimed=True, telegram_id=claimant.telegram_id)
    )
    if taken.rowcount != 1:
        await session.rollback()
        raise GiftClaimError(409, "Этот подарок уже кто-то забрал")

    days = payment.days or 30
    label = plan_label(days)
    name = await sender_name(payment, session)
    session.add(GiftNotification(
        recipient_id=claimant.telegram_id, sender_name=name, plan_label=label, plan_days=days,
    ))
    await _grant_subscription(claimant, days, session)
    return {
        "plan_label": label, "plan_days": days, "sender_name": name,
        "message": payment.gift_message or "", "sender_id": payment.gift_sender_id,
        "expires_at": claimant.subscription_expires_at,
    }


async def notify_gift_claimed(bot: Bot, sender_id: int | None, label: str) -> None:
    if not sender_id or sender_id <= 0:
        return
    try:
        await bot.send_message(
            sender_id,
            f"✅ <b>Ваш подарок забрали!</b>\n\n📦 {label}\nПолучатель уже пользуется VPN 🎉",
            parse_mode="HTML",
        )
    except Exception as e:  # noqa: BLE001 — уведомление необязательно
        logger.warning("Gift claim sender notify failed: %s", e)


async def notify_gift_recipient(
    payment: Payment, recipient: User, label: str, bot: Bot, session: AsyncSession,
) -> None:
    """Старые подарки конкретному человеку: окно в мини-аппе/кабинете +
    сообщение получателю в Telegram с учётом анонимности."""
    from bot.handlers.gift import _instructions_kb

    name = await sender_name(payment, session)
    session.add(GiftNotification(
        recipient_id=recipient.telegram_id, sender_name=name, plan_label=label,
        plan_days=payment.days or 30,
    ))
    await session.commit()

    exp = recipient.subscription_expires_at
    exp_str = exp.strftime("%d.%m.%Y") if exp else "—"
    personal = f"\n\n💬 <i>«{html.escape(payment.gift_message)}»</i>" if payment.gift_message else ""
    text = (
        f"🎁 <b>Тебе подарили подписку STAR VPN!</b>\n\n"
        f"От: <b>{html.escape(name)}</b>\n"
        f"📦 Тариф: <b>{label}</b>\n"
        f"⏳ Действует до: <b>{exp_str}</b>"
        f"{personal}\n\n"
        f"Нажми <b>📱 Моя подписка</b> чтобы подключиться."
    )
    try:
        await bot.send_message(recipient.telegram_id, text, parse_mode="HTML",
                               reply_markup=_instructions_kb())
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not notify gift recipient %s: %s", recipient.telegram_id, e)
