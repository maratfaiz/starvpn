from datetime import datetime, timedelta

from bot.models.device import Device
from bot.models.payment import Payment
from bot.tasks import scheduler
from tests.conftest import make_user


async def test_expired_users_notified_and_disabled(session, fake_marzban, bot, monkeypatch):
    now = datetime.utcnow()
    expired = now - timedelta(minutes=10)
    await make_user(session, 1, trial_used=True, subscription_expires_at=expired)  # пробный
    await make_user(session, 2, trial_used=True, subscription_expires_at=expired)  # получил подарок
    await make_user(session, 3, subscription_expires_at=expired)                   # без устройств
    await make_user(session, -4, email="w@b.cd", subscription_expires_at=expired)  # веб-аккаунт
    session.add(Payment(order_id="g", telegram_id=2, amount=99, status="paid", is_gift=True))
    await fake_marzban.create_user(1, now, username="tg_1_d1")
    session.add(Device(telegram_id=1, slot=1, name="ios", marzban_username="tg_1_d1"))
    await session.commit()

    emails: list[tuple[str, str]] = []

    async def fake_email(to, subject, text):
        emails.append((to, subject))

    monkeypatch.setattr("bot.utils.mailer.send_subscription_email", fake_email)
    monkeypatch.setattr(scheduler.asyncio, "sleep", _no_sleep)

    await scheduler.deactivate_expired_subscriptions(bot, now - timedelta(hours=1), now)

    texts = dict(bot.sent)
    assert "Пробный период закончился" in texts[1]
    assert "Подписка истекла" in texts[2]
    assert 3 in texts
    assert emails == [("w@b.cd", "Подписка STAR VPN истекла")]
    assert fake_marzban.users["tg_1_d1"]["status"] == "disabled"


async def test_warning_window_skips_already_expired(session, bot, monkeypatch):
    now = datetime.utcnow()
    await make_user(session, 1, subscription_expires_at=now - timedelta(hours=5))
    await make_user(session, 2, subscription_expires_at=now + timedelta(hours=20))
    monkeypatch.setattr(scheduler.asyncio, "sleep", _no_sleep)
    # Простой 3 суток: since далеко в прошлом.
    await scheduler.check_expiring_subscriptions(bot, now - timedelta(days=3), now)
    assert [chat for chat, _ in bot.sent] == [2]


async def _no_sleep(_):
    return None
