"""
🎁 Подарить подписку — покупка VPN-подписки для другого пользователя.

Флоу:
  1. Нажал «🎁 Подарить VPN» → выбирает тариф (inline)
  2. Выбирает способ оплаты: ⭐ Stars или 💎 Крипта  (GiftForm.pay_method)
  3. Вводит @username или ID получателя (GiftForm.recipient)
  4. Выбирает: анонимно или нет (GiftForm.anon_choice)
  5. Пишет личное сообщение (GiftForm.personal_message, только для Stars; можно пропустить)
  6. Stars  → answer_invoice (XTR)
     Крипта → create_invoice CryptoPay → ссылка на @CryptoBot
  7. После оплаты → подписка активируется получателю, оба получают уведомления
"""

import logging
from datetime import datetime, timedelta

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
from sqlalchemy import select

from bot.models.device import Device
from bot.models.gift_notification import GiftNotification
from bot.models.payment import Payment
from bot.models.user import User
from bot.states.payment_states import GiftForm
from bot.utils.cryptopay import cryptopay, CRYPTO_PLANS
from bot.utils.database import AsyncSessionLocal
from bot.utils.marzban import marzban

router = Router()
logger = logging.getLogger(__name__)

PLANS: dict[str, dict] = {
    "plan_1m": {"days": 30,  "stars": 99,  "label": "1 месяц",   "desc": "30 дней безлимитного VPN"},
    "plan_3m": {"days": 90,  "stars": 200, "label": "3 месяца",  "desc": "90 дней · скидка 11%"},
    "plan_6m": {"days": 180, "stars": 370, "label": "6 месяцев", "desc": "180 дней · скидка 18%"},
}

# Временное хранилище личных сообщений до подтверждения оплаты (только Stars)
# ключ: "sender_id:recipient_id"
_pending_messages: dict[str, str] = {}


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")]
    ])


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


@router.message(F.text == "🎁 Подарить VPN")
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


# ──────────────────────── Шаг 3 — ввод получателя ───────────────────────────

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
    await state.set_state(GiftForm.recipient)

    data = await state.get_data()
    plan = PLANS[data["gift_plan"]]
    method_label = "⭐ Telegram Stars" if method == "stars" else "💎 Криптовалюта"

    await callback.message.edit_text(
        f"🎁 Подарок: <b>{plan['label']}</b> · {method_label}\n\n"
        "👤 Введи <b>@username</b> или <b>ID</b> получателя:",
        parse_mode="HTML",
        reply_markup=_cancel_kb(),
    )
    await callback.answer()


# ──────────────────────── Шаг 4 — выбор анонимности ─────────────────────────

@router.message(GiftForm.recipient)
async def gift_enter_recipient(message: Message, state: FSMContext, session: AsyncSession) -> None:
    arg = (message.text or "").strip()
    if not arg:
        await message.answer("Введи @username или числовой ID.", reply_markup=_cancel_kb())
        return

    # Поиск пользователя в БД
    if arg.lstrip("-").isdigit():
        result = await session.execute(
            select(User).where(User.telegram_id == int(arg))
        )
    else:
        result = await session.execute(
            select(User).where(User.username == arg.lstrip("@"))
        )
    recipient: User | None = result.scalar_one_or_none()

    if not recipient:
        await message.answer(
            f"❌ Пользователь <b>{arg}</b> не найден.\n\n"
            "Возможно, он ещё не запустил бота — попроси его написать "
            "<b>/start</b> в @starisvpnbot, затем попробуй снова.\n\n"
            "Или введи другой @username / ID:",
            parse_mode="HTML",
            reply_markup=_cancel_kb(),
        )
        return

    if recipient.telegram_id == message.from_user.id:
        await message.answer(
            "❌ Нельзя подарить подписку самому себе.",
            reply_markup=_cancel_kb(),
        )
        return

    data = await state.get_data()
    plan = PLANS[data["gift_plan"]]
    method = data.get("gift_method", "stars")
    await state.update_data(gift_recipient_id=recipient.telegram_id)
    await state.set_state(GiftForm.anon_choice)

    uname = f"@{recipient.username}" if recipient.username else str(recipient.telegram_id)
    method_label = "⭐ Stars" if method == "stars" else "💎 Крипта"

    await message.answer(
        f"🎁 Получатель: <b>{uname}</b>\n"
        f"Тариф: <b>{plan['label']}</b> · {method_label}\n\n"
        "Отправить <b>анонимно</b> или <b>от своего имени</b>?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🕵️ Анонимно",       callback_data="gift_anon:1"),
                InlineKeyboardButton(text="👤 От моего имени",  callback_data="gift_anon:0"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")],
        ]),
    )


# ──────────────────────── Шаг 5 — личное сообщение (только Stars) ───────────

@router.callback_query(F.data.startswith("gift_anon:"), GiftForm.anon_choice)
async def gift_choose_anon(callback: CallbackQuery, state: FSMContext) -> None:
    anon = callback.data.split(":", 1)[1]
    await state.update_data(gift_anon=anon)

    data = await state.get_data()
    method = data.get("gift_method", "stars")

    if method == "crypto":
        # Для крипты личное сообщение не поддерживается — сразу к оплате
        await state.update_data(gift_personal_message="")
        await callback.answer()
        await _send_gift_invoice(callback.message, state, data, "")
        return

    # Stars — спрашиваем личное сообщение
    await state.set_state(GiftForm.personal_message)
    await callback.message.edit_text(
        "✍️ <b>Хочешь добавить личное сообщение получателю?</b>\n\n"
        "Напиши что-нибудь тёплое — оно придёт вместе с подарком 🎁\n"
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
    recipient_id = data.get("gift_recipient_id")
    anon = data.get("gift_anon", "0")
    method = data.get("gift_method", "stars")

    if not plan_key or not recipient_id:
        await msg.answer("Ошибка. Начни заново.")
        await state.clear()
        return

    await state.clear()

    plan = PLANS[plan_key]
    sender_id = msg.chat.id

    anon_label = "Анонимно 🕵️" if anon == "1" else "От твоего имени 👤"

    if method == "crypto":
        # ── Крипто-подарок ──────────────────────────────────────────────────
        crypto_plan = CRYPTO_PLANS.get(plan_key)
        if not crypto_plan:
            await msg.answer("❌ Крипто-тариф не найден.")
            return

        payload_str = f"gift:{plan_key}:{recipient_id}:{anon}:{sender_id}"

        try:
            invoice = await cryptopay.create_invoice(
                usd_amount=crypto_plan["usd"],
                payload=payload_str,
                description=f"STAR VPN Подарок — {plan['label']}",
            )
        except Exception as e:
            logger.error("CryptoPay gift invoice failed sender=%s: %s", sender_id, e)
            await msg.answer(
                "❌ Не удалось создать крипто-счёт. Попробуй позже или выбери оплату ⭐ Stars."
            )
            return

        invoice_id = invoice.get("invoice_id")
        pay_url = invoice.get("bot_invoice_url") or invoice.get("mini_app_invoice_url", "")

        # Сохраняем pending-платёж в БД
        async with AsyncSessionLocal() as session:
            payment = Payment(
                order_id=f"crypto_gift_{invoice_id}",
                telegram_id=sender_id,
                amount=float(crypto_plan["usd"]),
                status="pending",
                payment_method="crypto",
                invoice_id=invoice_id,
                days=plan["days"],
            )
            session.add(payment)
            await session.commit()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💎 Оплатить ${crypto_plan['usd']} через @CryptoBot",
                url=pay_url,
            )],
        ])

        await msg.answer(
            f"💎 <b>Счёт для подарка создан!</b>\n\n"
            f"📦 Тариф: <b>{plan['label']}</b>\n"
            f"💵 Сумма: <b>${crypto_plan['usd']}</b>\n"
            f"Отправка: {anon_label}\n\n"
            f"Нажми кнопку и оплати через @CryptoBot.\n"
            f"Подписка активируется получателю <b>автоматически</b> ✅\n\n"
            f"⏱ Счёт действителен 1 час.",
            parse_mode="HTML",
            reply_markup=kb,
        )

    else:
        # ── Stars-подарок ────────────────────────────────────────────────────
        if personal_message:
            _pending_messages[f"{sender_id}:{recipient_id}"] = personal_message

        payload = f"gift:{plan_key}:{recipient_id}:{anon}"
        msg_label = (
            f"\n✍️ Сообщение: <i>{personal_message[:50]}{'...' if len(personal_message) > 50 else ''}</i>"
            if personal_message else ""
        )

        await msg.answer(
            f"🎁 <b>Подтверди оплату</b>\n\n"
            f"Тариф: <b>{plan['label']}</b> — {plan['stars']} ⭐\n"
            f"Отправка: {anon_label}"
            f"{msg_label}",
            parse_mode="HTML",
        )

        await msg.answer_invoice(
            title=f"🎁 Подарок STAR VPN — {plan['label']}",
            description=f"Подарочная подписка на {plan['days']} дней",
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label=f"Подарок: {plan['label']}", amount=plan["stars"])],
        )


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

async def handle_gift_payment(
    message: Message,
    payload: str,
    session: AsyncSession,
) -> None:
    """Вызывается из payment.py при успешной оплате gift-invoice (Stars)."""
    try:
        parts = payload.split(":", 3)
        if len(parts) != 4:
            raise ValueError("wrong parts count")
        _, plan_key, recipient_id_str, anon_str = parts
    except ValueError:
        logger.error("Malformed gift payload: %s", payload)
        return

    plan = PLANS.get(plan_key)
    if not plan:
        logger.error("Unknown plan in gift payload: %s", plan_key)
        return

    recipient_id = int(recipient_id_str)
    anon = anon_str == "1"
    sender_id = message.from_user.id

    # Достаём личное сообщение
    personal_message = _pending_messages.pop(f"{sender_id}:{recipient_id}", "")

    result = await session.execute(select(User).where(User.telegram_id == recipient_id))
    recipient: User | None = result.scalar_one_or_none()
    if not recipient:
        await message.answer("❌ Получатель не найден. Обратись в поддержку.")
        return

    # Активируем подписку получателю
    if recipient.marzban_username:
        try:
            await marzban.extend_user(recipient.marzban_username, plan["days"])
        except Exception as e:
            logger.error("Marzban extend failed for gift recipient %s: %s", recipient_id, e)
    else:
        try:
            mz = await marzban.create_user(
                recipient_id, plan["days"],
                note=f"gift|from:{sender_id}|tg:{recipient_id}",
            )
            recipient.marzban_username = mz["username"]
            dev = Device(
                telegram_id=recipient_id,
                slot=1,
                name="ios",
                marzban_username=mz["username"],
            )
            session.add(dev)
        except Exception as e:
            logger.error("Marzban create failed for gift recipient %s: %s", recipient_id, e)

    now = datetime.utcnow()
    base = (
        recipient.subscription_expires_at
        if recipient.subscription_expires_at and recipient.subscription_expires_at > now
        else now
    )
    recipient.subscription_expires_at = base + timedelta(days=plan["days"])

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

    personal_block = f"\n\n💬 <i>«{personal_message}»</i>" if personal_message else ""

    notif_text = (
        f"🎁 <b>Тебе подарили подписку STAR VPN!</b>\n\n"
        f"От: <b>{sender_name}</b>\n"
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
