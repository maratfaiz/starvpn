import re
from datetime import datetime, timedelta

import pytest

from bot.handlers.devices import new_device_mz_username
from bot.models.device import Device
from bot.utils.marzban import marzban
from tests.conftest import make_user


async def test_names_are_readable_unique_and_skip_deleted_devices(session):
    user = await make_user(session, 42, username="Bob_K")
    assert await new_device_mz_username(user, "ios", session) == "bob_k_iphone_42"

    session.add(Device(telegram_id=42, slot=1, name="ios", marzban_username="bob_k_iphone_42",
                       is_active=False))
    await session.commit()
    # Удалённое устройство тоже занимает имя — новое получает новый ключ.
    assert await new_device_mz_username(user, "ios", session) == "bob_k_iphone2_42"
    assert await new_device_mz_username(user, "windows", session) == "bob_k_windows_42"


async def test_name_falls_back_to_transliterated_name(session):
    user = await make_user(session, 7)
    user.username, user.full_name = None, "Иван Петров"
    assert await new_device_mz_username(user, "androidtv", session) == "ivan_tv_7"


async def test_web_account_names_fit_marzban_limit(session):
    tg_id = -(2 ** 62)
    user = await make_user(session, tg_id)
    user.username, user.email = None, "very.long.email.address.for.test@example.com"
    name = await new_device_mz_username(user, "android", session)
    assert name.endswith(f"_android_w{2 ** 62}") and len(name) <= 32
    assert re.fullmatch(r"[a-z0-9][a-z0-9_]*[a-z0-9]", name)


async def test_get_or_create_does_not_resurrect_expired(fake_marzban):
    import httpx

    past = datetime.utcnow() - timedelta(days=1)
    with pytest.raises(httpx.HTTPStatusError):
        await marzban.get_or_create_user("tg_1_d1", 1, past)
    assert "tg_1_d1" not in fake_marzban.users

    future = datetime.utcnow() + timedelta(days=3)
    user = await marzban.get_or_create_user("tg_1_d1", 1, future)
    assert user["expire"] == future
