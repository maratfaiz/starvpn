"""
⚡️ Подключить VPN — покупка подписки через Telegram Stars (XTR).
🎁 Пробный период — 2-дневный бесплатный тест.

Тарифы:
  1 месяц  —  99 ⭐
  3 месяца — 249 ⭐  (скидка 16%)
  6 месяцев— 449 ⭐  (скидка 25%)

Флоу Stars:
  1. Пользователь выбирает тариф → бот отправляет invoice (currency=XTR)
  2. Telegram показывает стандартный экран оплаты
  3. pre_checkout_query → немедленно отвечаем ok=True
  4. successful_payment → продлеваем подписку в Marzban, уведомляем юзера + админа
"""

import logging
from datetime import datetime, timedelta

from aiogram import Bot, Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.config import settings
from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.marzban import marzban
from bot.utils.bot_media import send_screen
from bot.utils import gifts
from bot.utils.bot_texts import MenuText, image_for, t
from bot.utils.plans import STARS_PLANS
from bot.handlers.gift import handle_gift_payment

router = Router()
logger = logging.getLogger(__name__)

INSTRUCTIONS_TEXT = {
    "ios": (
        "🍏 <b>iPhone / iPad</b>\n\n"
        "<b>Вариант 1 — Streisand</b> (рекомендуем)\n"
        "1. Скачай <a href=\"https://apps.apple.com/app/id6446544843\">Streisand</a> из App Store\n"
        "2. Нажми «+» → «Import from Clipboard»\n"
        "3. Вставь ссылку → «Connect» ✅\n\n"
        "<b>Вариант 2 — V2Box</b> (если Streisand недоступен)\n"
        "1. Скачай <a href=\"https://apps.apple.com/app/id6446814690\">V2Box</a> из App Store\n"
        "2. «+» → «Import from Clipboard»\n"
        "3. Вставь ссылку → Connect ✅\n\n"
        "<b>Вариант 3 — Hiddify</b>\n"
        "1. Скачай <a href=\"https://apps.apple.com/app/id6596777532\">Hiddify</a> из App Store\n"
        "2. «+» → вставь ссылку → подключись ✅"
    ),
    "android": (
        "🤖 <b>Android — v2rayNG</b>\n\n"
        "1. Скачай <a href=\"https://play.google.com/store/apps/details?id=com.v2ray.ang\">v2rayNG</a> из Google Play\n"
        "2. Нажми «+» → вставь VLESS-ссылку\n"
        "3. Нажми ▶️ — подключено ✅"
    ),
    "windows": (
        "💻 <b>Windows — v2rayN</b>\n\n"
        "1. Скачай <a href=\"https://github.com/2dust/v2rayN/releases\">v2rayN</a> с GitHub\n"
        "2. «Сервера» → «Импортировать из буфера»\n"
        "3. Вставь VLESS-ссылку → ✅"
    ),
    "macos": (
        "🍎 <b>macOS — V2Box</b>\n\n"
        "1. Скачай <a href=\"https://apps.apple.com/app/id6446814690\">V2Box</a> из Mac App Store\n"
        "2. «+» → «Import from Clipboard»\n"
        "3. Вставь VLESS-ссылку → Connect ✅"
    ),
}


def _instructions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn.instructions"), callback_data="instr:pick"),
    ]])


# Обработчики instr:* живут только в instructions.py — дубликаты удалены


PLANS = STARS_PLANS

REFERRAL_DAYS_BONUS = 30      # дней рефереру за каждую пачку оплативших рефералов
REFERRAL_MILESTONE_SIZE = 2   # сколько оплативших рефералов нужно для одной пачки

# Разовые бейджи-достижения по общему числу оплативших рефералов — выдаются
# один раз, ровно когда referral_count достигает threshold, поверх обычных
# пачек выше. Порядок важен для отображения в /partner.
REFERRAL_ACHIEVEMENTS = [
    {"key": "first",      "threshold": 1,  "icon": "🥉", "title": "Первая ласточка",  "bonus_days": 5},
    {"key": "ambassador", "threshold": 5,  "icon": "🥈", "title": "Амбассадор",       "bonus_days": 20},
    {"key": "legend",     "threshold": 10, "icon": "🥇", "title": "Легенда STAR VPN", "bonus_days": 50},
    {"key": "vip",        "threshold": 25, "icon": "💎", "title": "Партнёр года",     "bonus_days": 150},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _grant_subscription(user: User, days: int, session: AsyncSession) -> None:
    """Добавить days к подписке: в БД и у всех устройств в Marzban, и закоммитить.

    Новый срок считается один раз (от текущего, если он в будущем, иначе
    от сейчас) и выставляется устройствам ровно таким же — раньше каждое
    устройство продлевалось от своего срока в Marzban, и сроки расходились.
    Продление заодно включает устройства, выключенные по истечении
    подписки (кроме забаненных — их доступ включает только разбан).

    Коммит — единственный в функции: вызывающий код может до вызова
    изменить другие строки (например, пометить платёж оплаченным), и они
    сохранятся вместе с продлением — или не сохранятся вовсе."""
    now = datetime.utcnow()
    base = (
        user.subscription_expires_at
        if user.subscription_expires_at and user.subscription_expires_at > now
        else now
    )
    new_expiry = base + timedelta(days=days)

    devices_result = await session.execute(
        select(Device).where(Device.telegram_id == user.telegram_id, Device.is_active.is_(True))
    )
    names = [d.marzban_username for d in devices_result.scalars().all()]

    if not names and user.marzban_username:
        # Старый формат (один аккаунт без устройств) — переносим в devices.
        # Если такое устройство уже есть, но удалено пользователем, —
        # не воскрешаем его (и не ловим UNIQUE на повторной вставке).
        existing = await session.execute(
            select(Device.id).where(Device.marzban_username == user.marzban_username)
        )
        if existing.scalar_one_or_none() is None:
            session.add(Device(
                telegram_id=user.telegram_id,
                slot=1,
                name="ios",
                marzban_username=user.marzban_username,
            ))
            names.append(user.marzban_username)

    activate = not user.is_banned
    for name in names:
        try:
            await marzban.set_expire(name, new_expiry, activate=activate)
        except Exception as e:
            logger.warning("Marzban set_expire %s failed: %s", name, e)

    user.subscription_expires_at = new_expiry
    await session.commit()


async def _credit_referral(buyer: User, session: AsyncSession, bot: Bot) -> None:
    """
    +30 дней рефереру за каждые 2 оплативших подписку реферала, плюс разовые
    бейджи-достижения (REFERRAL_ACHIEVEMENTS) при первом/5-м/10-м/25-м
    оплатившем друге. Считается один раз на человека
    (buyer.referral_bonus_counted), а не на каждую его покупку/продление —
    иначе один и тот же реферал накручивал бы счётчик при каждом продлении.
    """
    if not buyer.referrer_id or buyer.referral_bonus_counted:
        return

    result = await session.execute(
        select(User).where(User.telegram_id == buyer.referrer_id)
    )
    referrer: User | None = result.scalar_one_or_none()
    if not referrer:
        return

    buyer.referral_bonus_counted = True
    referrer.referral_count = (referrer.referral_count or 0) + 1

    bonus_lines: list[str] = []
    total_bonus_days = 0
    unlocked_achievement = None

    if referrer.referral_count % REFERRAL_MILESTONE_SIZE == 0:
        total_bonus_days += REFERRAL_DAYS_BONUS
        bonus_lines.append(f"🎁 +{REFERRAL_DAYS_BONUS} дней — за {referrer.referral_count} оплативших друзей")

    unlocked_achievement = next(
        (a for a in REFERRAL_ACHIEVEMENTS if a["threshold"] == referrer.referral_count), None
    )
    if unlocked_achievement:
        total_bonus_days += unlocked_achievement["bonus_days"]
        bonus_lines.append(
            f"{unlocked_achievement['icon']} +{unlocked_achievement['bonus_days']} дней — "
            f"достижение «{unlocked_achievement['title']}»"
        )

    if total_bonus_days:
        await _grant_subscription(referrer, total_bonus_days, session)
        referrer.extra_days_granted = (referrer.extra_days_granted or 0) + total_bonus_days
        try:
            header = "🏆 <b>Новое достижение!</b>" if unlocked_achievement else "🎉 <b>Бонус за рефералов!</b>"
            await bot.send_message(
                referrer.telegram_id,
                f"{header}\n\n" + "\n".join(bonus_lines) +
                f"\n\nВсего оплативших друзей: <b>{referrer.referral_count}</b>. "
                f"Подписка продлена автоматически.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to notify referrer %s: %s", referrer.telegram_id, e)

    await session.commit()

    logger.info(
        "Referral: tg_id=%s now has %s paying referrals (buyer tg_id=%s, +%s days)",
        referrer.telegram_id, referrer.referral_count, buyer.telegram_id, total_bonus_days,
    )


async def _notify_admin_purchase(bot: Bot, user: User, plan: dict) -> None:
    uname = f"@{user.username}" if user.username else f"ID {user.telegram_id}"
    try:
        await bot.send_message(
            settings.telegram_admin_id,
            f"⭐ <b>Новая подписка!</b>\n"
            f"Пользователь: {uname} (<code>{user.telegram_id}</code>)\n"
            f"Тариф: <b>{plan['label']}</b> · {plan['stars']} ⭐",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning("Admin notify failed: %s", e)


# ---------------------------------------------------------------------------
# ⚡️ Подключить VPN — выбор тарифа
# ---------------------------------------------------------------------------

def _plans_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            text=f"{plan['label']} — {plan['stars']} ⭐",
            callback_data=f"buy:{key}",
        )]
        for key, plan in PLANS.items()
    ]
    buttons.append([InlineKeyboardButton(
        text=t("btn.gift_friend"),
        callback_data="gift:start",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _stars_enabled(session: AsyncSession) -> bool:
    from bot.utils.settings_store import is_provider_enabled
    return await is_provider_enabled(session, "stars")


@router.message(MenuText("btn.connect"))
async def show_plans(message: Message, session: AsyncSession) -> None:
    if not await _stars_enabled(session):
        from bot.handlers.profile import _pay_choice_kb, pay_choice_text
        await send_screen(
            message, await pay_choice_text(), image=image_for("pay.choose"),
            reply_markup=await _pay_choice_kb(),
        )
        return
    await send_screen(message, t("plans.text"), image=image_for("plans.text"), reply_markup=_plans_keyboard())


@router.callback_query(F.data == "show_plans")
async def show_plans_inline(callback: CallbackQuery, session: AsyncSession) -> None:
    """Вызывается из инлайн-кнопок стартового сообщения."""
    if not await _stars_enabled(session):
        from bot.handlers.profile import _pay_choice_kb, pay_choice_text
        await send_screen(
            callback.message, await pay_choice_text(), image=image_for("pay.choose"),
            reply_markup=await _pay_choice_kb(),
        )
        await callback.answer()
        return
    await send_screen(
        callback.message, t("plans.text"), image=image_for("plans.text"), reply_markup=_plans_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def send_invoice(callback: CallbackQuery) -> None:
    plan_key = callback.data.split(":", 1)[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await callback.answer("Неизвестный тариф.", show_alert=True)
        return

    await callback.message.answer_invoice(
        title=f"STAR VPN — {plan['label']}",
        description=plan["desc"],
        payload=plan_key,
        currency="XTR",
        prices=[LabeledPrice(label=plan["label"], amount=plan["stars"])],
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# pre_checkout — ОБЯЗАТЕЛЬНО ответить за 10 секунд
# ---------------------------------------------------------------------------

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, session: AsyncSession) -> None:
    """Последний момент, когда можно отказаться от платежа до списания звёзд.
    Раньше здесь всегда был ok=True: звёзды списывались и за неизвестный
    тариф, и за подарок несуществующему получателю, и при выключенных Stars."""
    error = await _pre_checkout_error(query, session)
    if error:
        await query.answer(ok=False, error_message=error)
    else:
        await query.answer(ok=True)


async def _pre_checkout_error(query: PreCheckoutQuery, session: AsyncSession) -> str | None:
    from bot.handlers.gift import parse_stars_gift_payload

    payload = query.invoice_payload or ""
    if not await _stars_enabled(session):
        return "Оплата Stars сейчас недоступна. Выберите другой способ оплаты."
    buyer = await session.get(User, query.from_user.id)
    if not buyer:
        return "Сначала отправьте боту /start."
    if buyer.is_banned:
        return "Аккаунт заблокирован."

    link_payment_id = gifts.parse_link_payload(payload)
    if link_payment_id is not None:
        gift = await session.get(Payment, link_payment_id)
        if (not gift or gift.status != "pending" or gift.payment_method != "stars"
                or gift.gift_sender_id != buyer.telegram_id):
            return "Счёт устарел — оформите подарок заново."
        return None

    if payload.startswith("gift:"):
        parsed = parse_stars_gift_payload(payload)
        if not parsed or parsed[0] not in PLANS:
            return "Неизвестный тариф."
        _, recipient_id, _, payment_id = parsed
        if payment_id is not None:
            gift = await session.get(Payment, payment_id)
            if not gift or gift.status != "pending" or gift.gift_sender_id != buyer.telegram_id:
                return "Счёт устарел — оформите подарок заново."
        recipient = await session.get(User, recipient_id)
        if not recipient or recipient.is_banned:
            return "Получатель не найден."
        return None

    if payload not in PLANS:
        return "Неизвестный тариф."
    return None


@router.callback_query(F.data == "gift:start")
async def gift_start_from_plans(callback: CallbackQuery) -> None:
    """Переход к подарку из меню тарифов — тот же экран, что у кнопки
    «🎁 Подарить» (с учётом включённых способов оплаты). Раньше здесь
    отправлялся ReplyKeyboardRemove, и у пользователя пропадало главное меню."""
    from bot.handlers.gift import gift_start
    await gift_start(callback.message)
    await callback.answer()


# ---------------------------------------------------------------------------
# successful_payment — активация подписки
# ---------------------------------------------------------------------------

@router.message(F.successful_payment)
async def on_stars_payment(message: Message, session: AsyncSession) -> None:
    payment: SuccessfulPayment = message.successful_payment
    plan_key = payment.invoice_payload

    # Подарочные инвойсы: запись о платеже, звёзды покупателя и подписка
    # получателю — внутри handle_gift_payment.
    if plan_key.startswith(("gift:", gifts.LINK_PAYLOAD_PREFIX)):
        await handle_gift_payment(message, plan_key, session)
        return

    plan = PLANS.get(plan_key)

    if not plan:
        logger.error("Unknown plan in Stars payload: %s", plan_key)
        return

    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        return

    stars = payment.total_amount
    # Запись о платеже коммитится вместе с продлением (коммит в _grant_subscription).
    session.add(Payment(
        order_id=f"stars_{tg_id}_{payment.telegram_payment_charge_id}",
        telegram_id=tg_id,
        amount=float(stars),
        status="paid",
        payment_method="stars",
        days=plan["days"],
        paid_at=datetime.utcnow(),
    ))
    user.total_stars_paid = (user.total_stars_paid or 0) + stars
    await _grant_subscription(user, plan["days"], session)
    await session.refresh(user)  # баг 4: обновляем объект после commit

    await _credit_referral(user, session, message.bot)
    await _notify_admin_purchase(message.bot, user, plan)

    # Обновляем reply-клавиатуру + красивое сообщение об успехе
    from bot.handlers.start import main_keyboard
    exp = user.subscription_expires_at
    exp_str = exp.strftime("%d.%m.%Y") if exp else "—"

    await send_screen(
        message, t("paid.text", plan=plan["label"], expires=exp_str), image=image_for("paid.text"),
        reply_markup=main_keyboard(user),
    )


# ---------------------------------------------------------------------------
# 🎁 Пробный период
# ---------------------------------------------------------------------------

@router.message(MenuText("btn.trial"))
async def trial_menu(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await message.answer("Сначала отправь /start.")
        return

    if user.trial_used:
        await message.answer(
            t("trial.used"),
            parse_mode="HTML",
        )
        return

    await send_screen(
        message, t("trial.offer"), image=image_for("trial.offer"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn.activate_trial"), callback_data="activate_trial")]
        ]),
    )


@router.callback_query(F.data == "activate_trial")
async def activate_trial(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await callback.answer("Сначала отправь /start.", show_alert=True)
        return
    if user.trial_used:
        await callback.answer("Тест уже был активирован.", show_alert=True)
        return

    await callback.message.answer(t("trial.creating"))

    # Дни добавляются к текущему сроку (раньше — «сейчас + 2 дня», что
    # затирало оплаченную подписку) и включают уже созданные устройства.
    user.trial_used = True
    await _grant_subscription(user, settings.trial_days, session)
    await session.refresh(user)

    from bot.handlers.start import main_keyboard
    await send_screen(
        callback.message, t("trial.activated", days=settings.trial_days),
        image=image_for("trial.activated"), reply_markup=main_keyboard(user),
    )
    await callback.answer()
