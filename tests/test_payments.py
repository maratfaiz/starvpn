from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from bot.handlers import payment as payment_handlers
from bot.handlers.payment import _grant_subscription
from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from tests.conftest import make_user


async def _pending_crypto_payment(session, tg_id: int, invoice_id: int, days: int = 30) -> int:
    p = Payment(order_id=f"crypto_{invoice_id}", telegram_id=tg_id, amount=1.5, status="pending",
                payment_method="crypto", invoice_id=invoice_id, days=days)
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


async def test_crypto_webhook_failed_grant_is_retried(session, fake_marzban, bot, monkeypatch):
    from bot.handlers.crypto_payment import handle_crypto_webhook

    await make_user(session, 20)
    pid = await _pending_crypto_payment(session, 20, invoice_id=2020)

    async def broken_grant(user, days, session):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr(payment_handlers, "_grant_subscription", broken_grant)
    with pytest.raises(RuntimeError):
        await handle_crypto_webhook(2020, "USDT", bot)

    async with AsyncSessionLocal() as s:
        assert (await s.get(Payment, pid)).status == "pending"  # отметка откатилась

    monkeypatch.undo()
    await handle_crypto_webhook(2020, "USDT", bot)
    await handle_crypto_webhook(2020, "USDT", bot)  # повтор — без второй выдачи

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


def _stars_message(bot, tg_id: int, charge: str):
    async def answer(text, **kwargs):
        pass
    return SimpleNamespace(
        from_user=SimpleNamespace(id=tg_id, username="sender", full_name="S"),
        successful_payment=SimpleNamespace(total_amount=99, telegram_payment_charge_id=charge),
        bot=bot, answer=answer,
    )


async def test_stars_gift_link_is_paid_then_claimed_once(session, fake_marzban, bot):
    from bot.handlers.gift import handle_gift_payment
    from bot.utils import gifts

    await make_user(session, 40, username="sender")
    friend = await make_user(session, 41)
    other = await make_user(session, 42)
    gift = Payment(order_id="stars_gift_x", amount=99, payment_method="stars",
                   **gifts.link_gift_fields(40, 30, False, "С днём рождения!"))
    session.add(gift)
    await session.commit()
    gift_id, code = gift.id, gift.gift_link_code
    payload = gifts.link_payload(gift_id)
    assert await _pre_checkout_error(session, 40, payload) is None
    assert await _pre_checkout_error(session, 41, payload) is not None  # чужой счёт

    await handle_gift_payment(_stars_message(bot, 40, "ch1"), payload, session)
    await handle_gift_payment(_stars_message(bot, 40, "ch1"), payload, session)  # повтор

    async with AsyncSessionLocal() as s:
        paid = await s.get(Payment, gift_id)
        assert paid.status == "paid" and not paid.gift_claimed
        assert (await s.get(User, 40)).total_stars_paid == 99
        assert (await s.get(User, 41)).subscription_expires_at is None  # оплата не выдаёт дни
    links = [text for chat, text in bot.sent if chat == 40]
    assert len(links) == 1 and gifts.gift_url(code) in links[0]
    assert await _pre_checkout_error(session, 40, payload) is not None  # повторно не оплатить

    sender, friend, other = [await session.get(User, i) for i in (40, 41, 42)]
    with pytest.raises(gifts.GiftClaimError):
        await gifts.claim_gift(code, sender, session)  # свой подарок
    result = await gifts.claim_gift(code, friend, session)
    assert result["message"] == "С днём рождения!" and result["sender_name"] == "@sender"
    with pytest.raises(gifts.GiftClaimError):
        await gifts.claim_gift(code, other, session)

    async with AsyncSessionLocal() as s:
        claimed = await s.get(Payment, gift_id)
        assert claimed.gift_claimed and claimed.telegram_id == 41
        days = ((await s.get(User, 41)).subscription_expires_at - datetime.utcnow()).days
        assert 29 <= days <= 30
        assert (await s.get(User, 42)).subscription_expires_at is None


async def test_crypto_gift_link_webhook_sends_link_not_days(session, fake_marzban, bot):
    from bot.handlers.crypto_payment import handle_crypto_webhook
    from bot.utils import gifts

    await make_user(session, 45)
    session.add(Payment(order_id="crypto_gift_888", amount=1.5, payment_method="crypto",
                        invoice_id=888, **gifts.link_gift_fields(45, 30, True, "")))
    await session.commit()
    await handle_crypto_webhook(888, "USDT", bot, "giftlink:1")
    await handle_crypto_webhook(888, "USDT", bot, "giftlink:1")  # повторная доставка

    async with AsyncSessionLocal() as s:
        payment = (await s.execute(select(Payment).where(Payment.invoice_id == 888))).scalar_one()
        assert payment.status == "paid" and not payment.gift_claimed
        assert (await s.get(User, 45)).subscription_expires_at is None
    assert len([t for chat, t in bot.sent if chat == 45]) == 1


async def test_legacy_stars_gift_to_recipient_still_works(session, fake_marzban, bot):
    from bot.handlers.gift import handle_gift_payment

    await make_user(session, 46, username="sender")
    await make_user(session, 47)
    gift = Payment(order_id="stars_gift_old", telegram_id=47, amount=99, payment_method="stars",
                   days=30, is_gift=True, gift_sender_id=46, gift_anon=False,
                   gift_message="Привет", status="pending")
    session.add(gift)
    await session.commit()
    payload = f"gift:plan_1m:47:0:{gift.id}"
    assert await _pre_checkout_error(session, 46, payload) is None
    await handle_gift_payment(_stars_message(bot, 46, "ch2"), payload, session)
    async with AsyncSessionLocal() as s:
        assert (await s.get(Payment, gift.id)).status == "paid"
        assert (await s.get(User, 47)).subscription_expires_at > datetime.utcnow() + timedelta(days=29)
    assert any("Привет" in text for chat, text in bot.sent if chat == 47)


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
