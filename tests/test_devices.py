from datetime import datetime, timedelta

import pytest

from bot.handlers.devices import new_device_mz_username
from bot.models.device import Device
from bot.utils.marzban import marzban
from tests.conftest import make_user


async def test_names_use_telegram_id_and_skip_deleted_devices(session):
    await make_user(session, 42, username="bob")
    assert await new_device_mz_username(42, session) == "tg_42_d1"

    session.add(Device(telegram_id=42, slot=1, name="ios", marzban_username="tg_42_d1",
                       is_active=False))
    await session.commit()
    # Удалённое устройство тоже занимает имя — новое получает новый ключ.
    assert await new_device_mz_username(42, session) == "tg_42_d2"


async def test_web_account_names_fit_marzban_limit(session):
    tg_id = -(2 ** 62)
    await make_user(session, tg_id)
    name = await new_device_mz_username(tg_id, session)
    assert name.startswith("web_") and len(name) <= 32


async def test_get_or_create_does_not_resurrect_expired(fake_marzban):
    import httpx

    past = datetime.utcnow() - timedelta(days=1)
    with pytest.raises(httpx.HTTPStatusError):
        await marzban.get_or_create_user("tg_1_d1", 1, past)
    assert "tg_1_d1" not in fake_marzban.users

    future = datetime.utcnow() + timedelta(days=3)
    user = await marzban.get_or_create_user("tg_1_d1", 1, future)
    assert user["expire"] == future
