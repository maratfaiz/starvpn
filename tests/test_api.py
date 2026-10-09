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


async def test_site_plans_are_crypto_only_while_card_is_not_connected(session, monkeypatch):
    import pytest

    from bot.utils.cryptopay import cryptopay
    from bot.utils.settings_store import is_provider_enabled, set_provider_enabled

    monkeypatch.setattr(type(cryptopay), "configured", property(lambda self: True), raising=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        plans = (await client.get("/api/site/plans?days=47")).json()
    # Robokassa удалена (ADR-022): нет ни рублёвых цен, ни «своего срока».
    assert len(plans) == 3 and all(p["rub"] is None and p["usd"] for p in plans)

    assert not await is_provider_enabled(session, "card")
    with pytest.raises(ValueError):
        await set_provider_enabled(session, "card", True)



async def test_password_reset_flow(session, monkeypatch):
    from bot.utils import mailer
    from bot.utils.webauth import hash_password, verify_password
    from bot.models.user import User
    from bot.utils.database import AsyncSessionLocal

    sent: dict[str, str] = {}

    async def fake_send(to, code):
        sent[to] = code

    monkeypatch.setattr(mailer, "send_password_reset_email", fake_send)
    old_client = await _client_for(session, -9, email="r@e.st", email_verified=True,
                                   password_hash=hash_password("oldpassword"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        assert (await client.post("/api/account/forgot-password", json={"email": "no@one.xx"})).json()["ok"]
        assert "no@one.xx" not in sent
        await client.post("/api/account/forgot-password", json={"email": "r@e.st"})
        bad = await client.post("/api/account/reset-password",
                                json={"email": "r@e.st", "code": "000000", "password": "newpassword"})
        assert bad.status_code == 400 or sent["r@e.st"] == "000000"
        ok = await client.post("/api/account/reset-password",
                               json={"email": "r@e.st", "code": sent["r@e.st"], "password": "newpassword"})
        assert ok.status_code == 200 and "star_session" in ok.cookies
    async with AsyncSessionLocal() as s:
        assert verify_password("newpassword", (await s.get(User, -9)).password_hash)
    async with old_client:
        assert (await old_client.get("/api/me")).status_code == 401  # старая сессия закрыта
