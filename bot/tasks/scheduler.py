"""
Фоновые задачи — запускаются в том же event loop что и бот.

Задачи:
  • check_expiring_subscriptions — предупреждение за ~24 ч до истечения
  • deactivate_expired_subscriptions — деактивация устройств в Marzban при истечении
  • scheduler_loop — бесконечный цикл, запуск каждый час
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from bot.utils.marzban import marzban

logger = logging.getLogger(__name__)


def _renew_kb() -> InlineKeyboardMarkup:
    # sub:pay_choice, а не сразу Stars: способ оплаты может быть выключен.
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="sub:pay_choice"),
    ]])


def _first_month_stars() -> int:
    from bot.handlers.payment import PLANS
    return PLANS["plan_1m"]["stars"]


async def _paid_user_ids(ids: list[int]) -> set[int]:
    """Кто хоть раз платил — любым способом (раньше «платил» определялось по
    total_stars_paid, и все, кто платил картой/криптой, получали текст для
    пробного периода)."""
    if not ids:
        return set()
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(Payment.telegram_id).where(
                Payment.telegram_id.in_(ids), Payment.status == "paid", Payment.is_gift.is_(False),
            ).distinct()
        )
        return set(rows.scalars().all())


def _buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⚡️ Купить подписку", callback_data="show_plans"),
    ]])


# ─── Предупреждение за 24 часа ───────────────────────────────────────────────

async def check_expiring_subscriptions(bot: Bot, since: datetime, now: datetime) -> None:
    """Предупредить тех, у кого подписка кончается через 24 ч.

    Окно — (since, now] со сдвигом на 24 ч, где since — время прошлого
    прогона: каждое истечение попадает ровно в одно окно. Раньше окно было
    23–25 ч при запуске раз в час, и предупреждение приходило дважды.
    """
    window_from = since + timedelta(hours=24)
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
    paid = await _paid_user_ids([u.telegram_id for u in users])

    for user in users:
        is_trial = user.telegram_id not in paid
        try:
            if is_trial:
                await bot.send_message(
                    user.telegram_id,
                    "⏳ <b>Ваш пробный период заканчивается через 24 часа</b>\n\n"
                    "Надеемся, вы успели оценить скорость STAR VPN 🚀\n\n"
                    "Чтобы продолжить пользоваться без ограничений — "
                    "оформите полноценную подписку. "
                    f"Первый месяц всего за <b>{_first_month_stars()} ⭐</b>.",
                    parse_mode="HTML",
                    reply_markup=_buy_kb(),
                )
            else:
                exp = user.subscription_expires_at
                exp_str = exp.strftime("%d.%m.%Y") if exp else "—"
                await bot.send_message(
                    user.telegram_id,
                    f"⚠️ <b>Подписка истекает через 24 часа</b>\n\n"
                    f"Дата окончания: <b>{exp_str}</b>\n\n"
                    "Продлите сейчас — дни добавятся к текущей подписке, "
                    "ничего не потеряется.",
                    parse_mode="HTML",
                    reply_markup=_renew_kb(),
                )
            logger.info("Sent expiry warning to tg_id=%s (trial=%s)", user.telegram_id, is_trial)
        except Exception as e:
            logger.warning("Could not warn user %s about expiry: %s", user.telegram_id, e)
        await asyncio.sleep(0.05)


# ─── Деактивация при истечении ───────────────────────────────────────────────

async def deactivate_expired_subscriptions(bot: Bot, since: datetime, now: datetime) -> None:
    """
    Найти подписки, истёкшие с прошлого прогона (since, now], деактивировать
    все их устройства в Marzban и уведомить пользователей. Каждое истечение
    попадает ровно в один прогон (раньше окно 2 ч при запуске раз в час
    давало двойное уведомление).
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
        paid = await _paid_user_ids([u.telegram_id for u in users])

        for user in users:
            devs_result = await session.execute(
                select(Device).where(
                    Device.telegram_id == user.telegram_id,
                    Device.is_active.is_(True),
                )
            )
            devices = devs_result.scalars().all()

            if not devices:
                continue

            deactivated = 0
            for dev in devices:
                try:
                    await marzban.disable_user(dev.marzban_username)
                    deactivated += 1
                except Exception as e:
                    logger.warning(
                        "Failed to disable marzban user %s: %s",
                        dev.marzban_username, e,
                    )

            await session.commit()
            logger.info(
                "Deactivated %d/%d devices for expired user tg_id=%s",
                deactivated, len(devices), user.telegram_id,
            )

            # Уведомить пользователя
            is_trial = user.telegram_id not in paid
            try:
                if is_trial:
                    await bot.send_message(
                        user.telegram_id,
                        "🔒 <b>Пробный период закончился</b>\n\n"
                        "Спасибо, что попробовали STAR VPN!\n\n"
                        "Хотите продолжить? Оформите подписку — "
                        f"первый месяц всего за <b>{_first_month_stars()} ⭐</b>. "
                        "Все устройства уже настроены, просто продлите доступ.",
                        parse_mode="HTML",
                        reply_markup=_buy_kb(),
                    )
                else:
                    await bot.send_message(
                        user.telegram_id,
                        "⛔ <b>Подписка истекла</b>\n\n"
                        "Ваши устройства отключены от STAR VPN.\n"
                        "Продлите подписку — всё заработает снова мгновенно.",
                        parse_mode="HTML",
                        reply_markup=_renew_kb(),
                    )
            except Exception as e:
                logger.warning(
                    "Could not notify user %s about subscription expiry: %s",
                    user.telegram_id, e,
                )
            await asyncio.sleep(0.05)


# ─── Главный цикл ────────────────────────────────────────────────────────────

async def scheduler_loop(bot: Bot) -> None:
    """Запускается в asyncio.gather рядом с ботом. Тикает каждый час."""
    logger.info("Scheduler started — checks every 1 hour.")
    # Первый запуск через 60 секунд после старта бота
    await asyncio.sleep(60)

    # После рестарта догоняем последний час — как и раньше при окнах от now.
    last_tick = datetime.utcnow() - timedelta(hours=1)
    while True:
        now = datetime.utcnow()
        logger.info("Scheduler tick at %s UTC", now.strftime("%H:%M"))
        try:
            await check_expiring_subscriptions(bot, last_tick, now)
        except Exception as e:
            logger.error("check_expiring_subscriptions error: %s", e)

        try:
            await deactivate_expired_subscriptions(bot, last_tick, now)
        except Exception as e:
            logger.error("deactivate_expired_subscriptions error: %s", e)
        last_tick = now

        await asyncio.sleep(3600)  # следующий запуск через 1 час
