from bot.middlewares.user_sync import sync_user
from bot.models.user import User
from bot.utils.database import AsyncSessionLocal
from tests.conftest import make_user


async def test_username_moves_to_new_owner(session):
    await make_user(session, 1, username="Bob")
    await make_user(session, 2, username="alice")

    await sync_user(session, 1, "bob_new", "Bob")   # старый владелец сменил ник
    await sync_user(session, 2, "bob", "Alice")     # новый занял освободившийся

    async with AsyncSessionLocal() as s:
        assert (await s.get(User, 1)).username == "bob_new"
        assert (await s.get(User, 2)).username == "bob"


async def test_username_released_from_stale_holder(session):
    await make_user(session, 1, username="bob")  # не писал боту после смены ника
    await make_user(session, 2, username="x")
    await sync_user(session, 2, "BOB", "B")
    async with AsyncSessionLocal() as s:
        assert (await s.get(User, 1)).username is None
        assert (await s.get(User, 2)).username == "BOB"
