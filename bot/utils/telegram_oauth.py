"""
Вход через Telegram на сайте — OIDC (OpenID Connect) поверх oauth.telegram.org.

Это не Mini App и не классический Login Widget (data-onauth со скриптом
telegram-widget.js) — это полноценный OAuth 2.0 authorization code flow
с PKCE, который Telegram выдаёт через BotFather → бот → Login Widget
(там же Client ID/Client Secret/Redirect URIs/Trusted Origins).
См. https://core.telegram.org/bots/telegram-login
"""

import asyncio
import base64
import hashlib
import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from bot.config import settings

AUTHORIZE_URL = "https://oauth.telegram.org/auth"
TOKEN_URL = "https://oauth.telegram.org/token"
JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
ISSUER = "https://oauth.telegram.org"

logger = logging.getLogger(__name__)

# PyJWKClient сам кеширует ключи по URL — один клиент на процесс.
_jwks_client = PyJWKClient(JWKS_URL, timeout=10)

# Последняя ошибка входа — только для диагностики в админке (Настройки →
# «Вход через Telegram»). Без telegram_id/IP: только текст причины и время.
last_error: dict | None = None


class TelegramLoginError(Exception):
    """Ошибка входа с кодом, который /login показывает человеку."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def record_error(code: str, detail: str) -> None:
    global last_error
    last_error = {"code": code, "detail": detail[:500], "at": datetime.utcnow().isoformat()}
    logger.warning("Telegram OAuth: %s — %s", code, detail)


def is_configured() -> bool:
    return bool(settings.telegram_oauth_client_id and settings.telegram_oauth_client_secret)


def site_origin() -> str:
    # SITE_URL со слэшем на конце давал redirect_uri вида "https://x.ru//api/…",
    # который не совпадает с зарегистрированным в BotFather — Telegram отказывал.
    return settings.site_url.strip().rstrip("/")


def client_id() -> str:
    return settings.telegram_oauth_client_id.strip()


def redirect_uri() -> str:
    return f"{site_origin()}/api/telegram-oauth/callback"


def generate_pkce_pair() -> tuple[str, str]:
    """Возвращает (code_verifier, code_challenge) для PKCE (S256)."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str, code_verifier: str) -> dict:
    """POST /token — обменивает authorization code на id_token."""
    secret = settings.telegram_oauth_client_secret.strip()
    basic = base64.b64encode(f"{client_id()}:{secret}".encode("utf-8")).decode("ascii")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(),
                "client_id": client_id(),
                "code_verifier": code_verifier,
            },
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    if resp.status_code != 200:
        # Тело ответа — самое полезное для диагностики (invalid_client,
        # invalid_grant, redirect_uri mismatch…), без него причина не видна.
        raise TelegramLoginError("token", f"HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if not data.get("id_token"):
        raise TelegramLoginError("token", f"Нет id_token в ответе: {list(data)}")
    return data


async def verify_id_token(id_token: str) -> dict:
    """Проверяет подпись id_token через JWKS oauth.telegram.org и возвращает claims.

    aud проверяется вручную: PyJWT принимает только строку/список, а Telegram
    кладёт туда ID бота — если он придёт числом, штатная проверка падает с
    "Invalid claim format" даже на валидном токене. leeway — на расхождение
    часов сервера с Telegram (иначе "The token is not yet valid (iat)").
    """
    # PyJWKClient ходит в сеть синхронно — не блокируем event loop бота.
    signing_key = await asyncio.to_thread(_jwks_client.get_signing_key_from_jwt, id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "ES256", "EdDSA", "ES256K"],
        issuer=ISSUER,
        leeway=60,
        options={"verify_aud": False, "require": ["exp", "iat", "aud"]},
    )
    aud = claims.get("aud")
    auds = aud if isinstance(aud, list) else [aud]
    if client_id() not in {str(a) for a in auds}:
        raise TelegramLoginError("aud", f"aud={aud!r} не совпадает с TELEGRAM_OAUTH_CLIENT_ID")
    return claims


def telegram_id_from_claims(claims: dict) -> int:
    """Реальный Telegram ID — claim "id" (scope profile). "sub" — непрозрачный
    идентификатор OIDC, а не Telegram ID: подставлять его нельзя, иначе
    создался бы «чужой» пользователь с огромным несуществующим ID."""
    raw = claims.get("id")
    try:
        tg_id = int(raw)
    except (TypeError, ValueError):
        raise TelegramLoginError("claims", f"В id_token нет числового claim 'id' (есть: {sorted(claims)})")
    if tg_id <= 0:
        raise TelegramLoginError("claims", f"Некорректный id={tg_id}")
    return tg_id
