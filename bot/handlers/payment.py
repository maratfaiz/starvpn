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
from sqlalchemy import select, func

from bot.config import settings
from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.referral_credit import ReferralCredit
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from bot.utils.marzban import marzban
from bot.utils.qr import make_qr_photo
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
        InlineKeyboardButton(text="📚 Инструкции", callback_data="instr:pick"),
    ]])


# Обработчики instr:* живут только в instructions.py — дубликаты удалены


PLANS: dict[str, dict] = {
    "plan_1m": {"days": 30,  "stars": 99,  "label": "1 месяц",   "desc": "30 дней безлимитного VPN"},
    "plan_3m": {"days": 90,  "stars": 249, "label": "3 месяца",  "desc": "90 дней · скидка 16%"},
    "plan_6m": {"days": 180, "stars": 449, "label": "6 месяцев", "desc": "180 дней · скидка 25%"},
}

REFERRAL_DAYS_PER_REFERRAL = 15    # дней рефереру за каждого друга, оплатившего и оставшегося с нами
REFERRAL_VESTING_DAYS = 30         # сколько друг должен продержаться активным до начисления бонуса
REFERRAL_MONTHLY_CAP_DAYS = 90     # максимум реферальных дней за скользящие 30 дней на реферера (2026-08-31: было 365/365)

# Статусы-достижения по общему числу оплативших+переживших выдержку
# рефералов — чисто визуальные бейджи, без дополнительных дней (раньше
# стековались поверх REFERRAL_DAYS_BONUS и на 25 рефералах давали 585 дней —
# см. AGENTS/architecture/referral-system.md и AGENTS/decisions/ADR.md).
# Порядок важен для отображения в /partner.
REFERRAL_ACHIEVEMENTS = [
    {"key": "first",      "threshold": 1,  "icon": "🥉", "title": "Первая ласточка"},
    {"key": "ambassador", "threshold": 5,  "icon": "🥈", "title": "Амбассадор"},
    {"key": "legend",     "threshold": 10, "icon": "🥇", "title": "Легенда STAR VPN"},
    {"key": "vip",        "threshold": 25, "icon": "💎", "title": "Партнёр года"},
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

    if dev_list:
        for dev in dev_list:
            try:
                await marzban.extend_user(dev.marzban_username, days)
            except Exception as e:
                logger.warning("Marzban extend device %s failed: %s", dev.marzban_username, e)
    elif user.marzban_username:
        # Старый формат (без устройств) — продлеваем основной аккаунт
        try:
            await marzban.extend_user(user.marzban_username, days)
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


async def _mark_first_payment(buyer: User, session: AsyncSession) -> None:
    """
    Отмечает момент первой реальной самостоятельной оплаты покупателя —
    Stars, карта или крипта, но НЕ подарок (подарок — не покупка себе,
    его нельзя засчитывать как обращение реферала). С этого момента
    отсчитывается REFERRAL_VESTING_DAYS до начисления бонуса рефереру,
    см. credit_vested_referrals() в bot/tasks/scheduler.py. Ставится один
    раз и не двигается на повторных продлениях/покупках.
    """
    if buyer.first_payment_at is None:
        buyer.first_payment_at = datetime.utcnow()


async def credit_vested_referrals(bot: Bot) -> None:
    """
    Вызывается раз в час из scheduler_loop. Находит рефералов, чья первая
    самостоятельная оплата состоялась >= REFERRAL_VESTING_DAYS назад и ещё
    не была разобрана, и — если реферал всё ещё активный подписчик (не
    забанен, подписка не истекла) — начисляет его рефереру
    REFERRAL_DAYS_PER_REFERRAL дней, при условии что у реферера остался
    запас в пределах REFERRAL_MONTHLY_CAP_DAYS за последние 30 дней
    (скользящее окно, не календарный месяц — не "сбрасывается" 1-го числа).

    Это единственное место, где увеличивается referrer.referral_count —
    раньше он бился дважды (один раз на /start ещё до оплаты, второй раз
    здесь), из-за чего цифра "оплативших друзей" была завышена и не
    соответствовала реальности.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(days=REFERRAL_VESTING_DAYS)
    month_ago = now - timedelta(days=30)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.referrer_id.is_not(None),
                User.referral_bonus_counted.is_(False),
                User.first_payment_at.is_not(None),
                User.first_payment_at <= cutoff,
            )
        )
        vested_buyers = list(result.scalars().all())

        for buyer in vested_buyers:
            # Помечаем разобранным независимо от исхода ниже — это не retry-очередь,
            # у выдержки есть ровно один момент оценки.
            buyer.referral_bonus_counted = True

            still_active = bool(
                not buyer.is_banned
                and buyer.subscription_expires_at
                and buyer.subscription_expires_at > now
            )
            if not still_active:
                logger.info(
                    "Referral vesting: buyer tg_id=%s not active at vesting time — no credit",
                    buyer.telegram_id,
                )
                continue

            ref_result = await session.execute(
                select(User).where(User.telegram_id == buyer.referrer_id)
            )
            referrer: User | None = ref_result.scalar_one_or_none()
            if not referrer:
                continue

            credited_this_month = (await session.execute(
                select(func.coalesce(func.sum(ReferralCredit.days), 0)).where(
                    ReferralCredit.referrer_id == referrer.telegram_id,
                    ReferralCredit.created_at >= month_ago,
                )
            )).scalar_one()

            if credited_this_month >= REFERRAL_MONTHLY_CAP_DAYS:
                try:
                    await bot.send_message(
                        referrer.telegram_id,
                        "📈 <b>Месячный лимит реферальных дней достигнут</b>\n\n"
                        f"За последние 30 дней начислено {credited_this_month} дней — "
                        "это максимум. Новые оплатившие друзья по-прежнему учитываются "
                        "в статистике, но дни временно не начисляются.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("Failed to notify referrer %s about cap: %s", referrer.telegram_id, e)
                continue

            referrer.referral_count = (referrer.referral_count or 0) + 1
            days = REFERRAL_DAYS_PER_REFERRAL
            await _grant_subscription(referrer, days, session)
            referrer.extra_days_granted = (referrer.extra_days_granted or 0) + days
            session.add(ReferralCredit(referrer_id=referrer.telegram_id, referred_id=buyer.telegram_id, days=days))

            unlocked_achievement = next(
                (a for a in REFERRAL_ACHIEVEMENTS if a["threshold"] == referrer.referral_count), None
            )

            try:
                lines = [f"🎉 +{days} дней — друг оплатил подписку и остался с нами {REFERRAL_VESTING_DAYS} дней"]
                if unlocked_achievement:
                    lines.append(f"{unlocked_achievement['icon']} Новый статус: «{unlocked_achievement['title']}»!")
                await bot.send_message(
                    referrer.telegram_id,
                    "<b>Реферальный бонус!</b>\n\n" + "\n".join(lines) +
                    f"\n\nВсего оплативших друзей: <b>{referrer.referral_count}</b>. "
                    "Подписка продлена автоматически.",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning("Failed to notify referrer %s: %s", referrer.telegram_id, e)

            logger.info(
                "Referral vesting: credited referrer tg_id=%s +%s days (buyer tg_id=%s, total referrals=%s)",
                referrer.telegram_id, days, buyer.telegram_id, referrer.referral_count,
            )

        await session.commit()

    if vested_buyers:
        logger.info("Referral vesting check: processed %d buyers", len(vested_buyers))


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
        text="🎁 Подарить подписку другу",
        callback_data="gift:start",
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _stars_enabled(session: AsyncSession) -> bool:
    from bot.utils.settings_store import is_provider_enabled
    return await is_provider_enabled(session, "stars")


@router.message(F.text == "⚡️ Подключить VPN")
async def show_plans(message: Message, session: AsyncSession) -> None:
    if not await _stars_enabled(session):
        from bot.handlers.profile import _pay_choice_kb, pay_choice_text
        await message.answer(
            await pay_choice_text(), parse_mode="HTML", reply_markup=await _pay_choice_kb(),
        )
        return
    await message.answer(
        "⚡️ <b>Выберите тарифный план</b>\n\n"
        "Чем больше срок — тем выгоднее цена за месяц.\n"
        "Оплата в Telegram Stars ⭐ — мгновенно, без банков.",
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
        "⚡️ <b>Выберите тарифный план</b>\n\n"
        "Чем больше срок — тем выгоднее цена за месяц.\n"
        "Оплата в Telegram Stars ⭐ — мгновенно, без банков.",
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

    await _mark_first_payment(user, session)
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
        f"🎉 <b>Спасибо за покупку!</b>\n\n"
        f"📦 Тариф: <b>{plan['label']}</b>\n"
        f"⏳ Подписка действует до: <b>{exp_str}</b>\n\n"
        f"Теперь перейди в <b>📱 Моя подписка → Устройства → ➕ Добавить устройство</b> "
        f"и выбери тип своего устройства, чтобы получить ключ.",
        parse_mode="HTML",
        reply_markup=main_keyboard(user),
    )


# ---------------------------------------------------------------------------
# 🎁 Пробный период
# ---------------------------------------------------------------------------

@router.message(F.text == "🎁 Пробный период")
async def trial_menu(message: Message, session: AsyncSession) -> None:
    tg_id = message.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()

    if not user:
        await message.answer("Сначала отправь /start.")
        return

    if user.trial_used:
        await message.answer(
            "⚠️ <b>Тест уже был активирован</b>\n\n"
            "Пробный период можно использовать только один раз.\n"
            "Нажми <b>⚡️ Подключить VPN</b>, чтобы оформить подписку.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🎁 <b>Тестовый доступ</b>\n\n"
        "Мы дарим тебе <b>2 дня полного безлимита</b>, "
        "чтобы ты проверил скорость лично.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Активировать тест", callback_data="activate_trial")]
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

    await callback.message.answer("⏳ Создаю твой VPN-аккаунт...")

    user.trial_used = True
    user.subscription_expires_at = datetime.utcnow() + timedelta(days=settings.trial_days)
    await session.commit()
    await session.refresh(user)

    from bot.handlers.start import main_keyboard
    await callback.message.answer(
        f"✅ <b>Пробный период на {settings.trial_days} дня активирован!</b>\n\n"
        f"Теперь перейди в <b>📱 Моя подписка → Устройства → ➕ Добавить устройство</b> "
        f"и выбери тип своего устройства, чтобы получить ключ.",
        parse_mode="HTML",
        reply_markup=main_keyboard(user),
    )
    await callback.answer()
