"""
🎁 Подарить подписку — по ссылке (bot/utils/gifts.py).

Флоу:
  1. «🎁 Подарить VPN» → тариф (inline)
  2. Способ оплаты: ⭐ Stars или 💎 Крипта  (GiftForm.pay_method)
  3. Анонимно или от своего имени           (GiftForm.anon_choice)
  4. Личное сообщение (можно пропустить)    (GiftForm.personal_message)
  5. Stars → answer_invoice (XTR), крипта → счёт @CryptoBot;
     payload счёта — "giftlink:{payment_id}"
  6. После оплаты даритель получает ссылку {SITE_URL}/gift/{код} — и
     отправляет её кому угодно; получатель забирает подарок на сайте или
     через /start gift_{код}.

Раньше нужно было ввести @username получателя, и он должен был заранее
запустить бота. Счета старого формата ("gift:{plan}:{recipient}:…")
ещё обрабатываются — handle_gift_payment, ветка legacy.
"""

import html
import logging
import uuid

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from bot.models.gift_notification import GiftNotification
from bot.models.payment import Payment
from bot.models.user import User
from bot.states.payment_states import GiftForm
from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
from bot.utils.database import AsyncSessionLocal
from bot.utils.bot_texts import MenuText
from bot.utils import gifts
from bot.utils.plans import STARS_PLANS

router = Router()
logger = logging.getLogger(__name__)

PLANS = STARS_PLANS


def _instructions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📚 Инструкции", callback_data="instr:pick"),
    ]])


# ──────────────────────── Шаг 1 — выбор тарифа ──────────────────────────────

async def _crypto_enabled() -> bool:
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        return await is_provider_enabled(session, "crypto")


async def _stars_enabled() -> bool:
    from bot.utils.settings_store import is_provider_enabled
    async with AsyncSessionLocal() as session:
        return await is_provider_enabled(session, "stars")


@router.message(MenuText("btn.gift"))
async def gift_start(message: Message) -> None:
    crypto_on = await _crypto_enabled()
    stars_on = await _stars_enabled()
    if not stars_on and not crypto_on:
        await message.answer(
            "🎁 Подарки сейчас временно недоступны — оба способа оплаты подарков "
            "(⭐ Stars и 💎 крипта) отключены. Загляни попозже."
        )
        return

    buttons = []
    for key, plan in PLANS.items():
        crypto = CRYPTO_PLANS.get(key, {})
        price_parts = []
        if stars_on:
            price_parts.append(f"{plan['stars']} ⭐")
        if crypto and crypto_on:
            price_parts.append(f"${crypto['usd']}")
        buttons.append([InlineKeyboardButton(
            text=f"{plan['label']} — {' / '.join(price_parts)}",
            callback_data=f"gift_plan:{key}",
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")])

    await message.answer(
        "🎁 <b>Подарить подписку STAR VPN</b>\n\n"
        "Выбери тарифный план для подарка:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


# ──────────────────────── Шаг 2 — выбор способа оплаты ─────────────────────

@router.callback_query(F.data.startswith("gift_plan:"))
async def gift_choose_plan(callback: CallbackQuery, state: FSMContext) -> None:
    plan_key = callback.data.split(":", 1)[1]
    if plan_key not in PLANS:
        await callback.answer("Неизвестный тариф.", show_alert=True)
        return

    await state.update_data(gift_plan=plan_key)
    await state.set_state(GiftForm.pay_method)

    plan = PLANS[plan_key]
    crypto_on = await _crypto_enabled()
    stars_on = await _stars_enabled()
    crypto = CRYPTO_PLANS.get(plan_key, {})
    price_parts = []
    if stars_on:
        price_parts.append(f"{plan['stars']} ⭐")
    if crypto and crypto_on:
        price_parts.append(f"${crypto['usd']}")
    price_str = " / ".join(price_parts)

    rows = []
    if stars_on:
        rows.append([InlineKeyboardButton(text="⭐  Telegram Stars", callback_data="gift_method:stars")])
    if crypto_on:
        rows.append([InlineKeyboardButton(text="💎  Крипта  (USDT · TON · BTC · ETH)", callback_data="gift_method:crypto")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.edit_text(
        f"🎁 Подарок: <b>{plan['label']}</b> — {price_str}\n\n"
        "Выбери способ оплаты:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


# ──────────────────────── Шаг 3 — анонимность ───────────────────────────────

@router.callback_query(F.data.startswith("gift_method:"), GiftForm.pay_method)
async def gift_choose_method(callback: CallbackQuery, state: FSMContext) -> None:
    method = callback.data.split(":", 1)[1]  # "stars" or "crypto"
    if method == "crypto" and not await _crypto_enabled():
        await callback.answer("Оплата криптовалютой сейчас недоступна", show_alert=True)
        return
    if method == "stars" and not await _stars_enabled():
        await callback.answer("Оплата через Stars сейчас недоступна", show_alert=True)
        return
    await state.update_data(gift_method=method)
    await state.set_state(GiftForm.anon_choice)

    data = await state.get_data()
    plan = PLANS[data["gift_plan"]]
    method_label = "⭐ Telegram Stars" if method == "stars" else "💎 Криптовалюта"

    await callback.message.edit_text(
        f"🎁 Подарок: <b>{plan['label']}</b> · {method_label}\n\n"
        "После оплаты ты получишь <b>ссылку</b> — отправь её другу, и он заберёт "
        "подписку в боте или на сайте.\n\n"
        "Подписать подарок <b>своим именем</b> или отправить <b>анонимно</b>?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🕵️ Анонимно",       callback_data="gift_anon:1"),
                InlineKeyboardButton(text="👤 От моего имени",  callback_data="gift_anon:0"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")],
        ]),
    )
    await callback.answer()


# ──────────────────────── Шаг 5 — личное сообщение ──────────────────────────

@router.callback_query(F.data.startswith("gift_anon:"), GiftForm.anon_choice)
async def gift_choose_anon(callback: CallbackQuery, state: FSMContext) -> None:
    anon = callback.data.split(":", 1)[1]
    await state.update_data(gift_anon=anon)

    await state.set_state(GiftForm.personal_message)
    await callback.message.edit_text(
        "✍️ <b>Хочешь добавить личное сообщение получателю?</b>\n\n"
        "Напиши что-нибудь тёплое — получатель увидит его, когда откроет ссылку 🎁\n"
        "Или нажми <b>Пропустить</b>.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пропустить", callback_data="gift_msg:skip")],
            [InlineKeyboardButton(text="❌ Отмена",      callback_data="gift:cancel")],
        ]),
    )
    await callback.answer()


@router.message(GiftForm.personal_message)
async def gift_enter_message(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()[:300]
    data = await state.get_data()
    await state.update_data(gift_personal_message=text)
    await _send_gift_invoice(message, state, data, text)


@router.callback_query(F.data == "gift_msg:skip", GiftForm.personal_message)
async def gift_skip_message(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(gift_personal_message="")
    await callback.answer()
    await _send_gift_invoice(callback.message, state, data, "")


# ──────────────────────── Шаг 6 — отправка invoice ──────────────────────────

async def _send_gift_invoice(
    msg: Message,
    state: FSMContext,
    data: dict,
    personal_message: str,
) -> None:
    plan_key = data.get("gift_plan")
    anon = data.get("gift_anon", "0")
    method = data.get("gift_method", "stars")

    if not plan_key or plan_key not in PLANS:
        await msg.answer("Ошибка. Начни заново.")
        await state.clear()
        return

    await state.clear()

    plan = PLANS[plan_key]
    sender_id = msg.chat.id
    anon_label = "Анонимно 🕵️" if anon == "1" else "От твоего имени 👤"
    fields = gifts.link_gift_fields(sender_id, plan["days"], anon == "1", personal_message)

    if method == "crypto":
        crypto_plan = CRYPTO_PLANS.get(plan_key)
        if not crypto_plan:
            await msg.answer("❌ Крипто-тариф не найден.")
            return
        async with AsyncSessionLocal() as session:
            payment = Payment(order_id=f"crypto_gift_{uuid.uuid4().hex}",
                              amount=float(crypto_plan["usd"]), payment_method="crypto", **fields)
            session.add(payment)
            await session.flush()
            try:
                invoice = await cryptopay.create_invoice(
                    usd_amount=crypto_plan["usd"],
                    payload=gifts.link_payload(payment.id),
                    description=f"STAR VPN Подарок — {plan['label']}",
                )
            except Exception as e:  # noqa: BLE001 — любая ошибка CryptoPay = счёт не создан
                await session.rollback()
                logger.error("CryptoPay gift invoice failed sender=%s: %s", sender_id, e)
                await msg.answer(
                    "❌ Не удалось создать крипто-счёт. Попробуй позже или выбери оплату ⭐ Stars."
                )
                return
            payment.invoice_id = invoice.get("invoice_id")
            payment.order_id = f"crypto_gift_{payment.invoice_id}"
            await session.commit()
        pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url", "")

        await msg.answer(
            f"💎 <b>Счёт для подарка создан!</b>\n\n"
            f"📦 Тариф: <b>{plan['label']}</b>\n"
            f"💵 Сумма: <b>${crypto_plan['usd']}</b>\n"
            f"Подпись: {anon_label}\n\n"
            f"Оплати через @CryptoBot — сразу после оплаты пришлю ссылку на подарок 🎁\n\n"
            f"⏱ Счёт действителен 1 час.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
                text=f"💎 Оплатить ${crypto_plan['usd']} через @CryptoBot", url=pay_url,
            )]]),
        )
        return

    async with AsyncSessionLocal() as session:
        payment = Payment(order_id=f"stars_gift_{uuid.uuid4().hex}",
                          amount=float(plan["stars"]), payment_method="stars", **fields)
        session.add(payment)
        await session.commit()
        payment_id = payment.id
    msg_label = (
        f"\n✍️ Сообщение: <i>{html.escape(personal_message[:50])}{'...' if len(personal_message) > 50 else ''}</i>"
        if personal_message else ""
    )
    await msg.answer(
        f"🎁 <b>Подтверди оплату</b>\n\n"
        f"Тариф: <b>{plan['label']}</b> — {plan['stars']} ⭐\n"
        f"Подпись: {anon_label}"
        f"{msg_label}\n\n"
        f"После оплаты пришлю ссылку на подарок.",
        parse_mode="HTML",
    )
    await msg.answer_invoice(
        title=f"🎁 Подарок STAR VPN — {plan['label']}",
        description=f"Подарочная подписка на {plan['days']} дней — придёт ссылкой",
        payload=gifts.link_payload(payment_id),
        currency="XTR",
        prices=[LabeledPrice(label=f"Подарок: {plan['label']}", amount=plan["stars"])],
    )


def parse_stars_gift_payload(payload: str) -> tuple[str, int, bool, int | None] | None:
    """gift:{plan}:{recipient}:{anon}[:{payment_id}] → (plan, recipient, anon, payment_id).
    Четырёхчастный формат — счета, выставленные до появления pending-платежа."""
    parts = payload.split(":")
    if len(parts) not in (4, 5) or parts[0] != "gift":
        return None
    try:
        recipient_id = int(parts[2])
        payment_id = int(parts[4]) if len(parts) == 5 else None
    except ValueError:
        return None
    return parts[1], recipient_id, parts[3] == "1", payment_id


# ──────────────────────── Отмена ─────────────────────────────────────────────

@router.callback_query(F.data == "gift:cancel")
async def gift_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text("❌ Подарок отменён.")
    except Exception:
        await callback.message.answer("❌ Подарок отменён.")
    await callback.answer()


# ──────────────────────── Активация после оплаты Stars ───────────────────────

async def _handle_link_gift_payment(message: Message, payment_id: int, session: AsyncSession) -> None:
    """Подарок по ссылке оплачен звёздами: отметить оплату (атомарно — повтор
    апдейта ничего не делает), учесть звёзды покупателя и прислать ему ссылку.
    Подписку никто не получает, пока ссылку не откроют (gifts.claim_gift)."""
    from datetime import datetime

    paid = message.successful_payment
    if paid is None or message.from_user is None:
        return
    claimed = await session.execute(
        update(Payment)
        .where(Payment.id == payment_id, Payment.status == "pending",
               Payment.gift_sender_id == message.from_user.id)
        .values(status="paid", paid_at=datetime.utcnow(),
                order_id=f"gift_{message.from_user.id}_{paid.telegram_payment_charge_id}")
    )
    if claimed.rowcount != 1:
        await session.rollback()
        logger.error("Stars gift-link payment %s: no pending row", payment_id)
        return
    buyer = await session.get(User, message.from_user.id)
    if buyer:
        buyer.total_stars_paid = (buyer.total_stars_paid or 0) + paid.total_amount
    await session.commit()
    payment = await session.get(Payment, payment_id)
    await gifts.send_gift_link(message.bot, payment)


async def handle_gift_payment(
    message: Message,
    payload: str,
    session: AsyncSession,
) -> None:
    """Вызывается из payment.py при успешной оплате подарочного счёта Stars.
    Подарок по ссылке — _handle_link_gift_payment; старые счета на
    конкретного получателя — выдача подписки получателю сразу."""
    from datetime import datetime

    link_payment_id = gifts.parse_link_payload(payload)
    if link_payment_id is not None:
        await _handle_link_gift_payment(message, link_payment_id, session)
        return

    # ── legacy: счёт на подарок конкретному человеку (до ADR-022) ──
    parsed = parse_stars_gift_payload(payload)
    plan = STARS_PLANS.get(parsed[0]) if parsed else None
    if not parsed or not plan:
        logger.error("Malformed gift payload: %s", payload)
        return
    _, recipient_id, anon, payment_id = parsed

    paid = message.successful_payment
    if paid is None or message.from_user is None:
        return
    sender_id = message.from_user.id
    stars = paid.total_amount
    charge_id = paid.telegram_payment_charge_id
    order_id = f"gift_{sender_id}_{charge_id}"

    payment = await session.get(Payment, payment_id) if payment_id else None
    if payment and payment.status == "pending":
        payment.status = "paid"
        payment.paid_at = datetime.utcnow()
        payment.order_id = order_id
        anon = payment.gift_anon
    else:
        # Счёт старого формата (без pending-платежа) — записываем оплату сейчас.
        payment = Payment(
            order_id=order_id, telegram_id=recipient_id, amount=float(stars), status="paid",
            paid_at=datetime.utcnow(), payment_method="stars", days=plan["days"], is_gift=True,
            gift_sender_id=sender_id, gift_anon=anon,
        )
        session.add(payment)
    personal_message = payment.gift_message or ""

    buyer = await session.get(User, sender_id)
    if buyer:
        buyer.total_stars_paid = (buyer.total_stars_paid or 0) + stars

    recipient = await session.get(User, recipient_id)
    if not recipient:
        # Сюда не доходит: pre_checkout отклоняет счёт без получателя.
        await session.commit()
        await message.answer("❌ Получатель не найден. Обратись в поддержку.")
        return

    # Активируем подписку получателю — та же логика, что при обычной оплате:
    # продлеваются и включаются все его устройства. Коммит один — вместе
    # с отметкой об оплате.
    from bot.handlers.payment import _grant_subscription
    await _grant_subscription(recipient, plan["days"], session)

    sender_name = "Аноним 🕵️" if anon else (
        f"@{message.from_user.username}" if message.from_user.username
        else message.from_user.full_name or "пользователь"
    )

    notif = GiftNotification(
        recipient_id=recipient_id,
        sender_name=sender_name,
        plan_label=plan["label"],
        plan_days=plan["days"],
    )
    session.add(notif)
    await session.commit()

    exp_str = recipient.subscription_expires_at.strftime("%d.%m.%Y")

    await message.answer(
        f"✅ <b>Подарок отправлен!</b>\n\n"
        f"📦 Тариф: <b>{plan['label']}</b>\n"
        f"{'🕵️ Отправлено анонимно' if anon else '👤 Отправлено от твоего имени'}",
        parse_mode="HTML",
    )

    personal_block = f"\n\n💬 <i>«{html.escape(personal_message)}»</i>" if personal_message else ""

    notif_text = (
        f"🎁 <b>Тебе подарили подписку STAR VPN!</b>\n\n"
        f"От: <b>{html.escape(sender_name)}</b>\n"
        f"📦 Тариф: <b>{plan['label']} ({plan['days']} дней)</b>\n"
        f"⏳ Действует до: <b>{exp_str}</b>"
        f"{personal_block}\n\n"
        f"Нажми <b>📱 Моя подписка</b> чтобы подключиться."
    )

    try:
        await message.bot.send_message(
            recipient_id,
            notif_text,
            parse_mode="HTML",
            message_effect_id="5046509860389126442",
            reply_markup=_instructions_kb(),
        )
    except Exception:
        try:
            await message.bot.send_message(
                recipient_id,
                notif_text,
                parse_mode="HTML",
                reply_markup=_instructions_kb(),
            )
        except Exception as e:
            logger.warning("Could not notify gift recipient %s: %s", recipient_id, e)
