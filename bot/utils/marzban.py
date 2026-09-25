"""
Async HTTP client for the Marzban REST API.
Docs: https://gozargah.github.io/marzban/en/docs/api

Key methods:
  POST /api/admin/token          — get JWT
  POST /api/user                 — create user
  GET  /api/user/{username}      — get user info (links, traffic, online_at)
  PUT  /api/user/{username}      — update user (extend expiry, status)
  DELETE /api/user/{username}    — delete user
  GET  /api/users?status=active  — list all users
"""

import time
from datetime import datetime, timedelta

import httpx

from bot.config import settings


class MarzbanClient:
    def __init__(self) -> None:
        self._base_url = settings.marzban_url.rstrip("/")
        self._token: str | None = None
        self._token_expires: float = 0.0

    def _http(self) -> httpx.AsyncClient:
        # verify=False — Marzban использует самоподписанный сертификат
        return httpx.AsyncClient(verify=False, timeout=15.0)

    async def _auth(self) -> str:
        """Получить или обновить JWT токен."""
        if self._token and time.monotonic() < self._token_expires:
            return self._token

        async with self._http() as client:
            resp = await client.post(
                f"{self._base_url}/api/admin/token",
                data={
                    "username": settings.marzban_username,
                    "password": settings.marzban_password,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        self._token = data["access_token"]
        self._token_expires = time.monotonic() + 3300
        return self._token

    async def _headers(self) -> dict:
        return {"Authorization": f"Bearer {await self._auth()}"}

    # ------------------------------------------------------------------
    # Управление пользователями
    # ------------------------------------------------------------------

    async def create_user(self, telegram_id: int, days: int, note: str = "", ip_limit: int = 0,
                          username: str | None = None) -> dict:
        """Создать VLESS+Reality пользователя в Marzban. Возвращает объект с полем 'links'."""
        username = username or f"tg_{telegram_id}"
        expire_ts = int((datetime.utcnow() + timedelta(days=days)).timestamp())

        payload = {
            "username": username,
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": ["VLESS_REALITY"]},
            "data_limit": 0,
            "expire": expire_ts,
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": note or f"tg:{telegram_id}",
            "ip_limit": ip_limit,
        }

        async with self._http() as client:
            resp = await client.post(
                f"{self._base_url}/api/user",
                json=payload,
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def extend_user(self, marzban_username: str, days: int, activate: bool = True) -> dict:
        """Продлить истечение у существующего пользователя.

        activate=True заодно включает его: по истечении подписки планировщик
        переводит устройства в status=disabled, и простое продление expire
        оставляло их выключенными — человек платил, а VPN не работал.
        """
        async with self._http() as client:
            resp = await client.get(
                f"{self._base_url}/api/user/{marzban_username}",
                headers=await self._headers(),
            )
            resp.raise_for_status()
            current = resp.json()

        now_ts = int(datetime.utcnow().timestamp())
        base_ts = max(current.get("expire") or now_ts, now_ts)
        new_expire = base_ts + days * 86400

        body: dict = {"expire": new_expire}
        if activate:
            body["status"] = "active"
        async with self._http() as client:
            resp = await client.put(
                f"{self._base_url}/api/user/{marzban_username}",
                json=body,
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_user(self, marzban_username: str) -> dict:
        """Получить данные пользователя (links, traffic, expire, online_at, status)."""
        async with self._http() as client:
            resp = await client.get(
                f"{self._base_url}/api/user/{marzban_username}",
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_or_create_user(self, marzban_username: str, telegram_id: int, days: int) -> dict:
        """Получить пользователя из Marzban; при 404 — создать с нужным сроком."""
        try:
            return await self.get_user(marzban_username)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return await self.create_user(
                    telegram_id=telegram_id,
                    days=max(days, 1),
                    username=marzban_username,
                )
            raise

    async def provision_user(
        self, marzban_username: str, telegram_id: int, days: int, note: str = "", ip_limit: int = 0,
    ) -> dict:
        """Создать пользователя, а если он уже есть (устройство удалили и
        добавили снова — имя то же) — включить его и выставить срок.
        Раньше в этом случае возвращался старый выключенный пользователь,
        и выданный ключ не работал."""
        try:
            return await self.create_user(
                telegram_id=telegram_id, days=days, note=note, ip_limit=ip_limit,
                username=marzban_username,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 409:
                raise
        expire_ts = int((datetime.utcnow() + timedelta(days=max(days, 1))).timestamp())
        async with self._http() as client:
            resp = await client.put(
                f"{self._base_url}/api/user/{marzban_username}",
                json={"expire": expire_ts, "status": "active"},
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def disable_user(self, marzban_username: str) -> dict:
        """Отключить пользователя (status = disabled)."""
        async with self._http() as client:
            resp = await client.put(
                f"{self._base_url}/api/user/{marzban_username}",
                json={"status": "disabled"},
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def enable_user(self, marzban_username: str) -> dict:
        """Включить пользователя обратно (status = active)."""
        async with self._http() as client:
            resp = await client.put(
                f"{self._base_url}/api/user/{marzban_username}",
                json={"status": "active"},
                headers=await self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_user(self, marzban_username: str) -> None:
        """Удалить пользователя из Marzban."""
        async with self._http() as client:
            resp = await client.delete(
                f"{self._base_url}/api/user/{marzban_username}",
                headers=await self._headers(),
            )
            resp.raise_for_status()

    async def get_all_users(self) -> list[dict]:
        """Вернуть список всех пользователей Marzban (с пагинацией)."""
        all_users: list[dict] = []
        offset = 0
        limit = 500

        async with self._http() as client:
            while True:
                resp = await client.get(
                    f"{self._base_url}/api/users",
                    params={"offset": offset, "limit": limit},
                    headers=await self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, dict):
                    batch = data.get("users", [])
                    total = data.get("total", 0)
                else:
                    batch = data
                    total = len(data)

                all_users.extend(batch)
                offset += len(batch)

                if not batch or offset >= total:
                    break

        return all_users

    async def list_users(self) -> list[dict]:
        """Алиас get_all_users для веб-панели."""
        return await self.get_all_users()

    def extract_vless_link(self, marzban_user: dict) -> str | None:
        """Первая VLESS-ссылка из объекта пользователя Marzban."""
        for link in marzban_user.get("links", []):
            if link.startswith("vless://"):
                return link
        return None


# Singleton
marzban = MarzbanClient()
