"""
Тесты бизнес-логики на SQLite (aiosqlite) с подменённым Marzban и ботом.

Запуск: pip install -r tests/requirements.txt && pytest
"""

import os
import tempfile
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles

_DB_FILE = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.setdefault("TELEGRAM_API_TOKEN", "123456:TEST")
os.environ.setdefault("TELEGRAM_ADMIN_ID", "1")
os.environ["SQLALCHEMY_DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE}"

from bot.models.user import Base  # noqa: E402


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(type_, compiler, **kw):  # noqa: ANN001, ANN201
    # SQLite автоинкрементит только INTEGER PRIMARY KEY.
    return "INTEGER"

from bot.utils import database  # noqa: E402
from bot.utils.marzban import marzban  # noqa: E402


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://marzban")
    return httpx.HTTPStatusError(
        str(status), request=request, response=httpx.Response(status, request=request),
    )


class FakeMarzban:
    """Хранит пользователей Marzban в памяти: {username: {"expire", "status", "links"}}."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.fail_set_expire = False

    async def create_user(self, telegram_id, expire_at, note="", ip_limit=0, username=None):
        username = username or f"tg_{telegram_id}"
        if username in self.users:
            raise _http_error(409)
        self.users[username] = {
            "username": username, "expire": expire_at, "status": "active",
            "links": [f"vless://{username}@host:443#x"],
        }
        return self.users[username]

    async def set_expire(self, name, expire_at, activate=True):
        if self.fail_set_expire:
            raise RuntimeError("marzban down")
        if name not in self.users:
            raise _http_error(404)
        self.users[name]["expire"] = expire_at
        if activate:
            self.users[name]["status"] = "active"
        return self.users[name]

    async def get_user(self, name):
        if name not in self.users:
            raise _http_error(404)
        return self.users[name]

    async def disable_user(self, name):
        if name not in self.users:
            raise _http_error(404)
        self.users[name]["status"] = "disabled"
        return self.users[name]

    async def enable_user(self, name):
        self.users[name]["status"] = "active"
        return self.users[name]


@pytest.fixture
def fake_marzban(monkeypatch):
    fake = FakeMarzban()
    for attr in ("create_user", "set_expire", "get_user", "disable_user", "enable_user"):
        monkeypatch.setattr(marzban, attr, getattr(fake, attr))
    # Реальные provision_user / get_or_create_user поверх подменённых примитивов.
    return fake


@pytest.fixture(autouse=True)
async def db():
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await database.engine.dispose()


@pytest.fixture
async def session():
    async with database.AsyncSessionLocal() as s:
        yield s


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))
        return SimpleNamespace(message_id=1)


@pytest.fixture
def bot():
    return FakeBot()


async def make_user(session, telegram_id: int, **kwargs):
    from bot.models.user import User

    user = User(telegram_id=telegram_id, full_name="Test", created_at=datetime.utcnow(), **kwargs)
    session.add(user)
    await session.commit()
    return user
