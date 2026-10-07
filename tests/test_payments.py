from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from bot.handlers import payment as payment_handlers
from bot.handlers.card_payment import handle_card_webhook
from bot.handlers.payment import _grant_subscription
from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from tests.conftest import make_user


async def _pending_card_payment(session, tg_id: int, days: int = 30) -> int:
    p = Payment(order_id=f"card_{tg_id}_{days}", telegram_id=tg_id, amount=199,
                status="pending", payment_method="card", days=days)
    session.add(p)
    await session.commit()
    return p.id


async def test_grant_sets_device_expiry_equal_to_subscription(session, fake_marzban):
    future = datetime.utcnow() + timedelta(days=5, hours=7)
    user = await make_user(session, 10, subscription_expires_at=future)
    await fake_marzban.create_user(10, datetime.utcnow(), username="tg_10_d1")
    session.add(Device(telegram_id=10, slot=1, name="ios", marzban_username="tg_10_d1"))
    await session.commit()

    await _grant_subscription(user, 30, session)

    assert user.subscription_expires_at == future + timedelta(days=30)
    assert fake_marzban.users["tg_10_d1"]["expire"] == user.subscription_expires_at


async def test_card_webhook_failed_grant_is_retried(session, fake_marzban, bot, monkeypatch):
    await make_user(session, 20)
    pid = await _pending_card_payment(session, 20)

    async def broken_grant(user, days, session):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr(payment_handlers, "_grant_subscription", broken_grant)
    with pytest.raises(RuntimeError):
        await handle_card_webhook(pid, bot, out_sum="199.00")

    async with AsyncSessionLocal() as s:
        assert (await s.get(Payment, pid)).status == "pending"  # отметка откатилась

    monkeypatch.undo()
    await handle_card_webhook(pid, bot, out_sum="199.00")
    await handle_card_webhook(pid, bot, out_sum="199.00")  # повтор — без второй выдачи

    async with AsyncSessionLocal() as s:
        assert (await s.get(Payment, pid)).status == "paid"
        user = await s.get(User, 20)
        days = (user.subscription_expires_at - datetime.utcnow()).days
        assert 29 <= days <= 30


async def _pre_checkout_error(session, tg_id: int, payload: str) -> str | None:
    query = SimpleNamespace(invoice_payload=payload, from_user=SimpleNamespace(id=tg_id))
    return await payment_handlers._pre_checkout_error(query, session)


async def test_pre_checkout_rejects_bad_payloads(session):
    await make_user(session, 30)
    await make_user(session, 31, is_banned=True)
    assert await _pre_checkout_error(session, 30, "plan_1m") is None
    assert await _pre_checkout_error(session, 30, "plan_x") == "Неизвестный тариф."
    assert await _pre_checkout_error(session, 31, "plan_1m") == "Аккаунт заблокирован."
    assert await _pre_checkout_error(session, 30, "gift:plan_1m:999:0") == "Получатель не найден."


async def test_stars_gift_keeps_personal_message(session, fake_marzban, bot):
    from bot.handlers.gift import create_stars_gift_payment, handle_gift_payment, stars_gift_payload

    await make_user(session, 40, username="sender")
    await make_user(session, 41)
    pid = await create_stars_gift_payment(99, dict(
        telegram_id=41, days=30, is_gift=True, gift_sender_id=40, gift_anon=False,
        gift_message="С днём рождения!", status="pending",
    ))
    payload = stars_gift_payload("plan_1m", 41, "0", pid)
    assert await _pre_checkout_error(session, 40, payload) is None

    answers: list[str] = []

    async def answer(text, **kwargs):
        answers.append(text)

    message = SimpleNamespace(
        from_user=SimpleNamespace(id=40, username="sender", full_name="S"),
        successful_payment=SimpleNamespace(total_amount=99, telegram_payment_charge_id="ch1"),
        bot=bot, answer=answer,
    )
    await handle_gift_payment(message, payload, session)

    async with AsyncSessionLocal() as s:
        paid = await s.get(Payment, pid)
        assert paid.status == "paid" and paid.is_gift
        recipient = await s.get(User, 41)
        assert recipient.subscription_expires_at > datetime.utcnow() + timedelta(days=29)
        assert (await s.get(User, 40)).total_stars_paid == 99
    assert any("С днём рождения!" in text for chat, text in bot.sent if chat == 41)
    # Повторно тот же счёт оплатить нельзя.
    assert await _pre_checkout_error(session, 40, payload) is not None
    rows = (await session.execute(select(Payment))).scalars().all()
    assert len(rows) == 1


async def test_crypto_gift_webhook_delivers_message_and_popup(session, fake_marzban, bot):
    from bot.handlers.crypto_payment import handle_crypto_webhook
    from bot.models.gift_notification import GiftNotification

    await make_user(session, 50, username="giver")
    await make_user(session, 51)
    session.add(Payment(
        order_id="crypto_gift_777", telegram_id=51, amount=1.5, status="pending",
        payment_method="crypto", invoice_id=777, days=30, is_gift=True,
        gift_sender_id=50, gift_anon=False, gift_message="Держи VPN",
    ))
    await session.commit()

    payload = "gift:plan_1m:51:0:50"
    await handle_crypto_webhook(777, "USDT", bot, payload)
    await handle_crypto_webhook(777, "USDT", bot, payload)  # повторная доставка

    async with AsyncSessionLocal() as s:
        recipient = await s.get(User, 51)
        days = (recipient.subscription_expires_at - datetime.utcnow()).days
        assert 29 <= days <= 30
        notifs = (await s.execute(select(GiftNotification))).scalars().all()
        assert len(notifs) == 1 and notifs[0].sender_name == "@giver"
    to_recipient = [text for chat, text in bot.sent if chat == 51]
    assert len(to_recipient) == 1 and "Держи VPN" in to_recipient[0]
    assert any(chat == 50 for chat, _ in bot.sent)


async def test_regrant_does_not_resurrect_deleted_legacy_device(session, fake_marzban):
    await make_user(session, 60, marzban_username="tg_60")
    await fake_marzban.create_user(60, datetime.utcnow(), username="tg_60")
    session.add(Device(telegram_id=60, slot=1, name="ios", marzban_username="tg_60",
                       is_active=False))
    await session.commit()
    user = await session.get(User, 60)
    await _grant_subscription(user, 30, session)  # раньше — IntegrityError на UNIQUE
    devices = (await session.execute(select(Device))).scalars().all()
    assert len(devices) == 1 and not devices[0].is_active
