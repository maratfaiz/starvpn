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
from datetime import datetime, timezone

import httpx

from bot.config import settings


def _ts(moment: datetime) -> int:
    """Naive-UTC datetime (как во всей БД) → unix timestamp."""
    return int(moment.replace(tzinfo=timezone.utc).timestamp())


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

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Запрос к API с токеном. При 401 (Marzban перезапустили, токен
        протух раньше срока) токен сбрасывается и запрос повторяется один
        раз — раньше все вызовы падали до истечения кэша токена (~55 мин)."""
        for attempt in range(2):
            async with self._http() as client:
                resp = await client.request(
                    method, f"{self._base_url}{path}", headers=await self._headers(), **kwargs,
                )
            if resp.status_code == 401 and attempt == 0:
                self._token = None
                self._token_expires = 0.0
                continue
            resp.raise_for_status()
            return resp
        raise RuntimeError("unreachable")

    # ------------------------------------------------------------------
    # Управление пользователями
    # ------------------------------------------------------------------

    async def create_user(self, telegram_id: int, expire_at: datetime, note: str = "",
                          ip_limit: int = 0, username: str | None = None) -> dict:
        """Создать VLESS+Reality пользователя в Marzban. Возвращает объект с полем 'links'.

        expire_at — точный момент окончания (UTC), тот же, что
        User.subscription_expires_at: раньше передавалось целое число дней,
        и ключ устройства жил до суток меньше оплаченной подписки."""
        username = username or f"tg_{telegram_id}"

        payload = {
            "username": username,
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": ["VLESS_REALITY"]},
            "data_limit": 0,
            "expire": _ts(expire_at),
            "data_limit_reset_strategy": "no_reset",
            "status": "active",
            "note": note or f"tg:{telegram_id}",
            "ip_limit": ip_limit,
        }
        resp = await self._request("POST", "/api/user", json=payload)
        return resp.json()

    async def set_expire(self, marzban_username: str, expire_at: datetime,
                         activate: bool = True) -> dict:
        """Выставить срок пользователя ровно в expire_at.

        activate=True заодно включает его: по истечении подписки планировщик
        переводит устройства в status=disabled, и простое продление expire
        оставляло их выключенными — человек платил, а VPN не работал."""
        body: dict = {"expire": _ts(expire_at)}
        if activate:
            body["status"] = "active"
        resp = await self._request("PUT", f"/api/user/{marzban_username}", json=body)
        return resp.json()

    async def extend_user(self, marzban_username: str, days: int, activate: bool = True) -> dict:
        """Продлить на days от текущего срока в Marzban (или от сейчас) —
        только для пользователей Marzban, которых нет в нашей БД (раздел
        «Серверы» админки). Для наших пользователей срок задаёт
        _grant_subscription через set_expire."""
        current = await self.get_user(marzban_username)
        now_ts = int(time.time())
        base_ts = max(current.get("expire") or now_ts, now_ts)
        new_expire = datetime.utcfromtimestamp(base_ts + days * 86400)
        return await self.set_expire(marzban_username, new_expire, activate=activate)

    async def get_user(self, marzban_username: str) -> dict:
        """Получить данные пользователя (links, traffic, expire, online_at, status)."""
        resp = await self._request("GET", f"/api/user/{marzban_username}")
        return resp.json()

    async def get_or_create_user(
        self, marzban_username: str, telegram_id: int, expires_at: datetime | None,
    ) -> dict:
        """Получить пользователя из Marzban; при 404 — создать заново, но только
        если подписка ещё действует (до expires_at). Раньше при истёкшей
        подписке создавался активный пользователь на 30 дней — бесплатный VPN.
        Иначе пробрасывает HTTPStatusError 404."""
        try:
            return await self.get_user(marzban_username)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
            if not expires_at or expires_at <= datetime.utcnow():
                raise
            return await self.create_user(
                telegram_id=telegram_id, expire_at=expires_at, username=marzban_username,
            )

    async def provision_user(
        self, marzban_username: str, telegram_id: int, expire_at: datetime, note: str = "",
        ip_limit: int = 0,
    ) -> dict:
        """Создать пользователя, а если он уже есть — включить его и выставить
        срок. Раньше в этом случае возвращался старый выключенный
        пользователь, и выданный ключ не работал."""
        try:
            return await self.create_user(
                telegram_id=telegram_id, expire_at=expire_at, note=note, ip_limit=ip_limit,
                username=marzban_username,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 409:
                raise
        return await self.set_expire(marzban_username, expire_at, activate=True)

    async def disable_user(self, marzban_username: str) -> dict:
        """Отключить пользователя (status = disabled)."""
        resp = await self._request(
            "PUT", f"/api/user/{marzban_username}", json={"status": "disabled"},
        )
        return resp.json()

    async def enable_user(self, marzban_username: str) -> dict:
        """Включить пользователя обратно (status = active)."""
        resp = await self._request(
            "PUT", f"/api/user/{marzban_username}", json={"status": "active"},
        )
        return resp.json()

    async def delete_user(self, marzban_username: str) -> None:
        """Удалить пользователя из Marzban."""
        await self._request("DELETE", f"/api/user/{marzban_username}")

    async def get_all_users(self) -> list[dict]:
        """Вернуть список всех пользователей Marzban (с пагинацией)."""
        all_users: list[dict] = []
        offset = 0
        limit = 500

        while True:
            resp = await self._request(
                "GET", "/api/users", params={"offset": offset, "limit": limit},
            )
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
