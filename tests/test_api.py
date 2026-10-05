import httpx

from bot.api import app
from bot.utils.webauth import SESSION_COOKIE_NAME, create_web_session
from tests.conftest import make_user


async def _client_for(session, tg_id: int, **user_kwargs) -> httpx.AsyncClient:
    user = await make_user(session, tg_id, **user_kwargs)
    token = await create_web_session(user, session)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test",
        cookies={SESSION_COOKIE_NAME: token},
    )


async def test_trial_is_telegram_only(session, fake_marzban):
    async with await _client_for(session, -555, email="a@b.cd") as client:
        r = await client.post("/api/trial")
        assert r.status_code == 403

    async with await _client_for(session, 555) as client:
        r = await client.post("/api/trial")
        assert r.status_code == 200
        r = await client.post("/api/trial")
        assert r.status_code == 400


async def test_master_key_only_registers_first_admin(session, monkeypatch):
    import pytest

    from bot.config import settings
    from bot.utils import admin_auth

    monkeypatch.setattr(settings, "admin_web_key", "master-key-123")
    first, _ = await admin_auth.register_admin("master-key-123", "owner", "password123", session)
    assert first.rank == "admin"
    with pytest.raises(ValueError, match="bad_invite_key"):
        await admin_auth.register_admin("master-key-123", "intruder", "password123", session)
    worker, _ = await admin_auth.register_admin(first.invite_key, "helper", "password123", session)
    assert worker.rank == "worker"
