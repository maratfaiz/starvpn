"""
Фоновые задачи — запускаются в том же event loop что и бот.

Задачи:
  • check_expiring_subscriptions — предупреждение за ~24 ч до истечения
  • deactivate_expired_subscriptions — деактивация устройств в Marzban при истечении
  • scheduler_loop — бесконечный цикл, запуск каждый час

Уведомления уходят в Telegram, а веб-аккаунтам без Telegram — на email.
Время прошлого прогона хранится в app_settings: после простоя сервиса
пропущенные истечения обрабатываются (раньше — только последний час).
"""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import or_, select

from bot.models.app_setting import AppSetting
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from bot.utils.vpn_access import set_vpn_enabled

logger = logging.getLogger(__name__)

LAST_TICK_KEY = "scheduler.last_tick"
MAX_CATCH_UP = timedelta(days=7)


def _renew_kb() -> InlineKeyboardMarkup:
    # sub:pay_choice, а не сразу Stars: способ оплаты может быть выключен.
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="sub:pay_choice"),
    ]])


def _buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚡️ Купить подписку", callback_data="show_plans"),
    ]])


async def _first_month_price() -> str | None:
    """Цена месяца в первом включённом способе оплаты — раньше всегда
    показывались звёзды, даже если Stars выключены в админке."""
    from bot.utils.card import CARD_PLANS, card_ready
    from bot.utils.cryptopay import CRYPTO_PLANS, cryptopay
    from bot.utils.plans import STARS_PLANS
    from bot.utils.settings_store import get_all_provider_states

    async with AsyncSessionLocal() as session:
        states = await get_all_provider_states(session)
    if states["stars"]:
        return f"{STARS_PLANS['plan_1m']['stars']} ⭐"
    if states["card"] and card_ready():
        return f"{CARD_PLANS['plan_1m']['rub']} ₽"
    if states["crypto"] and cryptopay.configured:
        return f"${CRYPTO_PLANS['plan_1m']['usd']}"
    return None


async def _trial_only_ids(users: Sequence[User]) -> set[int]:
    """Кто сидит только на пробном периоде: брал пробный и ни разу не получал
    дни иначе — ни оплатой, ни подарком, ни бонусом за рефералов. Раньше
    «не платил» = «пробный», и получатели подарков читали, что у них
    заканчивается пробный период."""
    candidates = [u.telegram_id for u in users if u.trial_used and not u.extra_days_granted]
    if not candidates:
        return set()
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(Payment.telegram_id).where(
                Payment.telegram_id.in_(candidates),
                Payment.status == "paid",
                # Неразобранный подарок по ссылке висит на дарителе — это не его дни.
                or_(Payment.gift_link_code.is_(None), Payment.gift_claimed.is_(True)),
            ).distinct()
        )
        had_paid_days = set(rows.scalars().all())
    return set(candidates) - had_paid_days


async def _notify(bot: Bot, user: User, text: str, kb: InlineKeyboardMarkup,
                  email_subject: str, email_text: str) -> None:
    if user.telegram_id > 0:
        await bot.send_message(user.telegram_id, text, parse_mode="HTML", reply_markup=kb)
    elif user.email:
        from bot.utils.mailer import send_subscription_email
        await send_subscription_email(user.email, email_subject, email_text)


# ─── Предупреждение за 24 часа ───────────────────────────────────────────────

async def check_expiring_subscriptions(bot: Bot, since: datetime, now: datetime) -> None:
    """Предупредить тех, у кого подписка кончается через 24 ч.

    Окно — (since, now] со сдвигом на 24 ч, где since — время прошлого
    прогона: каждое истечение попадает ровно в одно окно. Нижняя граница
    не раньше now: после долгого простоя уже истёкшие получают только
    уведомление об истечении, а не «осталось 24 часа».
    """
    window_from = max(since + timedelta(hours=24), now)
    window_to = now + timedelta(hours=24)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.subscription_expires_at > window_from,
                User.subscription_expires_at <= window_to,
                User.is_banned.is_(False),
            )
        )
        users = result.scalars().all()

    logger.info("Expiry check: %d users expiring in ~24h", len(users))
    if not users:
        return
    trial_only = await _trial_only_ids(users)
    price = await _first_month_price()
    price_line = f"Первый месяц всего за <b>{price}</b>." if price else ""

    for user in users:
        is_trial = user.telegram_id in trial_only
        exp = user.subscription_expires_at
        exp_str = exp.strftime("%d.%m.%Y") if exp else "—"
        try:
            if is_trial:
                await _notify(
                    bot, user,
                    "⏳ <b>Ваш пробный период заканчивается через 24 часа</b>\n\n"
                    "Надеемся, вы успели оценить скорость STAR VPN 🚀\n\n"
                    "Чтобы продолжить пользоваться без ограничений — "
                    f"оформите полноценную подписку. {price_line}",
                    _buy_kb(),
                    "Пробный период STAR VPN заканчивается через 24 часа",
                    "Ваш пробный период заканчивается через 24 часа. "
                    "Оформите подписку в личном кабинете, чтобы VPN продолжил работать.",
                )
            else:
                await _notify(
                    bot, user,
                    f"⚠️ <b>Подписка истекает через 24 часа</b>\n\n"
                    f"Дата окончания: <b>{exp_str}</b>\n\n"
                    "Продлите сейчас — дни добавятся к текущей подписке, "
                    "ничего не потеряется.",
                    _renew_kb(),
                    "Подписка STAR VPN истекает через 24 часа",
                    f"Подписка истекает {exp_str} (UTC). Продлите её в личном кабинете — "
                    "дни добавятся к текущей подписке.",
                )
            logger.info("Sent expiry warning to tg_id=%s (trial=%s)", user.telegram_id, is_trial)
        except Exception as e:
            logger.warning("Could not warn user %s about expiry: %s", user.telegram_id, e)
        await asyncio.sleep(0.05)


# ─── Деактивация при истечении ───────────────────────────────────────────────

async def deactivate_expired_subscriptions(bot: Bot, since: datetime, now: datetime) -> None:
    """
    Найти подписки, истёкшие с прошлого прогона (since, now], отключить все
    их VPN-аккаунты в Marzban и уведомить пользователей. Каждое истечение
    попадает ровно в один прогон. Уведомление получают и те, у кого нет
    ни одного устройства (раньше их пропускали молча).
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.subscription_expires_at > since,
                User.subscription_expires_at <= now,
                User.is_banned.is_(False),
            )
        )
        users = result.scalars().all()
        if not users:
            return
        trial_only = await _trial_only_ids(users)
        price = await _first_month_price()
        price_line = f"первый месяц всего за <b>{price}</b>. " if price else ""

        for user in users:
            # Устройства и старый «основной» аккаунт — тот же набор, что при бане.
            await set_vpn_enabled(user, session, False)
            logger.info("Disabled VPN for expired user tg_id=%s", user.telegram_id)

            is_trial = user.telegram_id in trial_only
            try:
                if is_trial:
                    await _notify(
                        bot, user,
                        "🔒 <b>Пробный период закончился</b>\n\n"
                        "Спасибо, что попробовали STAR VPN!\n\n"
                        f"Хотите продолжить? Оформите подписку — {price_line}"
                        "Все устройства уже настроены, просто продлите доступ.",
                        _buy_kb(),
                        "Пробный период STAR VPN закончился",
                        "Пробный период закончился. Оформите подписку в личном кабинете — "
                        "все устройства уже настроены, VPN заработает сразу.",
                    )
                else:
                    await _notify(
                        bot, user,
                        "⛔ <b>Подписка истекла</b>\n\n"
                        "Ваши устройства отключены от STAR VPN.\n"
                        "Продлите подписку — всё заработает снова мгновенно.",
                        _renew_kb(),
                        "Подписка STAR VPN истекла",
                        "Подписка истекла, устройства отключены. Продлите её в личном "
                        "кабинете — всё заработает снова сразу после оплаты.",
                    )
            except Exception as e:
                logger.warning(
                    "Could not notify user %s about subscription expiry: %s",
                    user.telegram_id, e,
                )
            await asyncio.sleep(0.05)


# ─── Главный цикл ────────────────────────────────────────────────────────────

async def _load_last_tick(now: datetime) -> datetime:
    async with AsyncSessionLocal() as session:
        row = await session.get(AppSetting, LAST_TICK_KEY)
    try:
        last = datetime.fromisoformat(row.value) if row else now - timedelta(hours=1)
    except ValueError:
        last = now - timedelta(hours=1)
    return max(last, now - MAX_CATCH_UP)


async def _save_last_tick(moment: datetime) -> None:
    async with AsyncSessionLocal() as session:
        row = await session.get(AppSetting, LAST_TICK_KEY)
        if row:
            row.value = moment.isoformat()
        else:
            session.add(AppSetting(key=LAST_TICK_KEY, value=moment.isoformat()))
        await session.commit()


async def scheduler_loop(bot: Bot) -> None:
    """Запускается в asyncio.gather рядом с ботом. Тикает каждый час."""
    logger.info("Scheduler started — checks every 1 hour.")
    # Первый запуск через 60 секунд после старта бота
    await asyncio.sleep(60)

    last_tick = await _load_last_tick(datetime.utcnow())
    while True:
        now = datetime.utcnow()
        logger.info("Scheduler tick at %s UTC (since %s)", now.strftime("%H:%M"), last_tick)
        try:
            await check_expiring_subscriptions(bot, last_tick, now)
        except Exception as e:
            logger.error("check_expiring_subscriptions error: %s", e)

        try:
            await deactivate_expired_subscriptions(bot, last_tick, now)
        except Exception as e:
            logger.error("deactivate_expired_subscriptions error: %s", e)
        last_tick = now
        try:
            await _save_last_tick(now)
        except Exception as e:
            logger.error("Scheduler: failed to persist last tick: %s", e)

        await asyncio.sleep(3600)  # следующий запуск через 1 час
