import httpx
import pytest

from bot.api import app
from bot.models.user import User
from bot.utils import app_config
from bot.utils.card import CARD_PLANS
from bot.utils.cryptopay import CRYPTO_PLANS
from bot.utils.plans import STARS_PLANS
from bot.utils.webauth import create_web_session
from tests.conftest import make_user


@pytest.fixture
async def clean_config(session):
    yield
    await app_config.save(session, {key: None for key in app_config.FIELDS})


async def test_prices_apply_everywhere_and_reset(session, clean_config):
    await app_config.save(session, {
        "price.stars.plan_1m": "120", "price.usd.plan_3m": "4.5", "price.rub.plan_6m": "950",
    })
    assert STARS_PLANS["plan_1m"]["stars"] == 120
    assert str(CRYPTO_PLANS["plan_3m"]["usd"]) == "4.50"
    assert CRYPTO_PLANS["plan_3m"]["desc"] == "90 дней · $4.50"  # старая «скидка 11%» уже неправда
    assert int(CARD_PLANS["plan_6m"]["rub"]) == 950

    await app_config.save(session, {"price.stars.plan_1m": None, "price.usd.plan_3m": None})
    assert STARS_PLANS["plan_1m"]["stars"] == 99
    assert CRYPTO_PLANS["plan_3m"]["desc"] == "90 дней · $3.99 · скидка 11%"


async def test_invalid_values_are_rejected_without_partial_save(session, clean_config):
    with pytest.raises(ValueError):
        await app_config.save(session, {"max_devices": "5", "trial_days": "0"})
    assert app_config.max_devices() == 3
    with pytest.raises(ValueError):
        await app_config.save(session, {"unknown": "1"})


async def test_trial_can_be_switched_off(session, fake_marzban, clean_config):
    await make_user(session, 777)
    await app_config.save(session, {"trial_enabled": False})
    user = await session.get(User, 777)
    token = await create_web_session(user, session)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test",
                                 cookies={"star_session": token}) as client:
        assert (await client.post("/api/trial")).status_code == 403
        await app_config.save(session, {"trial_enabled": None, "trial_days": "5"})
        r = await client.post("/api/trial")
        assert r.status_code == 200 and r.json()["days"] == 5


def test_telegram_client_id_comes_from_bot_token():
    assert app_config.tg_oauth_client_id() == "123456"  # TELEGRAM_API_TOKEN=123456:TEST
