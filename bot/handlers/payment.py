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
from bot.utils.bot_texts import MenuText, t
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


PLANS: dict[str, dict] = {
    "plan_1m": {"days": 30,  "stars": 99,  "label": "1 месяц",   "desc": "30 дней безлимитного VPN"},
    "plan_3m": {"days": 90,  "stars": 249, "label": "3 месяца",  "desc": "90 дней · скидка 16%"},
    "plan_6m": {"days": 180, "stars": 449, "label": "6 месяцев", "desc": "180 дней · скидка 25%"},
}

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
    """Создать или продлить аккаунт в Marzban, продлить все устройства и обновить БД."""
    from sqlalchemy import select as sa_select
    devices_result = await session.execute(
        sa_select(Device).where(Device.telegram_id == user.telegram_id, Device.is_active.is_(True))
    )
    dev_list = list(devices_result.scalars().all())

    # Продление заодно включает устройства, выключенные по истечении подписки
    # (кроме забаненных — их доступ включает только разбан).
    activate = not user.is_banned
    if dev_list:
        for dev in dev_list:
            try:
                await marzban.extend_user(dev.marzban_username, days, activate=activate)
            except Exception as e:
                logger.warning("Marzban extend device %s failed: %s", dev.marzban_username, e)
    elif user.marzban_username:
        # Старый формат (без устройств) — продлеваем основной аккаунт
        try:
            await marzban.extend_user(user.marzban_username, days, activate=activate)
        except Exception as e:
            logger.error("Marzban extend failed for %s: %s", user.marzban_username, e)
        # Создаём запись в devices для миграции
        dev = Device(
            telegram_id=user.telegram_id,
            slot=1,
            name="ios",
            marzban_username=user.marzban_username,
        )
        session.add(dev)
    else:
        # Новый пользователь — подписка активирована, устройство добавят сами
        pass

    now = datetime.utcnow()
    base = (
        user.subscription_expires_at
        if user.subscription_expires_at and user.subscription_expires_at > now
        else now
    )
    user.subscription_expires_at = base + timedelta(days=days)
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
        await message.answer(
            await pay_choice_text(), parse_mode="HTML", reply_markup=await _pay_choice_kb(),
        )
        return
    await message.answer(
        t("plans.text"),
        parse_mode="HTML",
        reply_markup=_plans_keyboard(),
    )


@router.callback_query(F.data == "show_plans")
async def show_plans_inline(callback: CallbackQuery, session: AsyncSession) -> None:
    """Вызывается из инлайн-кнопок стартового сообщения."""
    if not await _stars_enabled(session):
        from bot.handlers.profile import _pay_choice_kb, pay_choice_text
        await callback.message.answer(
            await pay_choice_text(), parse_mode="HTML", reply_markup=await _pay_choice_kb(),
        )
        await callback.answer()
        return
    await callback.message.answer(
        t("plans.text"),
        parse_mode="HTML",
        reply_markup=_plans_keyboard(),
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
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


# ---------------------------------------------------------------------------
# successful_payment — активация подписки
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "gift:start")
async def gift_start_from_plans(callback: CallbackQuery) -> None:
    """Переход к подарку из меню тарифов."""
    from aiogram.types import ReplyKeyboardRemove
    await callback.message.answer(
        "🎁 Нажми кнопку ниже в меню:",
        reply_markup=ReplyKeyboardRemove(),
    )
    # Эмулируем нажатие "🎁 Подарить VPN" — просто отправим текст
    await callback.message.answer("🎁 <b>Подарить подписку STAR VPN</b>\n\n"
        "Выбери тарифный план для подарка:", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            *[[InlineKeyboardButton(
                text=f"{plan['label']} — {plan['stars']} ⭐",
                callback_data=f"gift_plan:{key}",
            )] for key, plan in PLANS.items()],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")],
        ]),
    )
    await callback.answer()


@router.message(F.successful_payment)
async def on_stars_payment(message: Message, session: AsyncSession) -> None:
    payment: SuccessfulPayment = message.successful_payment
    plan_key = payment.invoice_payload

    # Обработка подарочных инвойсов
    if plan_key.startswith("gift:"):
        await handle_gift_payment(message, plan_key, session)
        # Сохранить платёж
        tg_id = message.from_user.id
        stars = payment.total_amount
        db_payment = Payment(
            order_id=f"gift_{tg_id}_{payment.telegram_payment_charge_id}",
            telegram_id=tg_id,
            amount=float(stars),
            status="paid",
            paid_at=datetime.utcnow(),
        )
        session.add(db_payment)
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        buyer = result.scalar_one_or_none()
        if buyer:
            buyer.total_stars_paid = (buyer.total_stars_paid or 0) + stars
        await session.commit()
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

    await _grant_subscription(user, plan["days"], session)
    await session.refresh(user)  # баг 4: обновляем объект после commit

    stars = payment.total_amount

    await _credit_referral(user, session, message.bot)
    await _notify_admin_purchase(message.bot, user, plan)

    db_payment = Payment(
        order_id=f"stars_{tg_id}_{payment.telegram_payment_charge_id}",
        telegram_id=tg_id,
        amount=float(stars),
        status="paid",
        paid_at=datetime.utcnow(),
    )
    session.add(db_payment)
    user.total_stars_paid = (user.total_stars_paid or 0) + stars
    await session.commit()

    # Обновляем reply-клавиатуру + красивое сообщение об успехе
    from bot.handlers.start import main_keyboard
    exp = user.subscription_expires_at
    exp_str = exp.strftime("%d.%m.%Y") if exp else "—"

    await message.answer(
        t("paid.text", plan=plan["label"], expires=exp_str),
        parse_mode="HTML",
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

    await message.answer(
        t("trial.offer"),
        parse_mode="HTML",
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
    await callback.message.answer(
        t("trial.activated", days=settings.trial_days),
        parse_mode="HTML",
        reply_markup=main_keyboard(user),
    )
    await callback.answer()
