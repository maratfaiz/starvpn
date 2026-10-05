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
