"""
Вход через Telegram на сайте — OIDC (OpenID Connect) поверх oauth.telegram.org.

Это не Mini App и не классический Login Widget (data-onauth со скриптом
telegram-widget.js) — это полноценный OAuth 2.0 authorization code flow
с PKCE, который Telegram выдаёт через BotFather → бот → Login Widget
(там же Client ID/Client Secret/Redirect URIs/Trusted Origins).
См. https://core.telegram.org/bots/telegram-login
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from bot.config import settings

AUTHORIZE_URL = "https://oauth.telegram.org/auth"
TOKEN_URL = "https://oauth.telegram.org/token"
JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
ISSUER = "https://oauth.telegram.org"

# PyJWKClient сам кеширует ключи по URL — один клиент на процесс.
_jwks_client = PyJWKClient(JWKS_URL)


def redirect_uri() -> str:
    return f"{settings.site_url}/api/telegram-oauth/callback"


def generate_pkce_pair() -> tuple[str, str]:
    """Возвращает (code_verifier, code_challenge) для PKCE (S256)."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "client_id": settings.telegram_oauth_client_id,
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
    basic = base64.b64encode(
        f"{settings.telegram_oauth_client_id}:{settings.telegram_oauth_client_secret}".encode("utf-8")
    ).decode("ascii")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(),
                "client_id": settings.telegram_oauth_client_id,
                "code_verifier": code_verifier,
            },
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    resp.raise_for_status()
    return resp.json()


def verify_id_token(id_token: str) -> dict:
    """Проверяет подпись id_token через JWKS oauth.telegram.org и возвращает claims."""
    signing_key = _jwks_client.get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256", "ES256", "EdDSA", "ES256K"],
        audience=settings.telegram_oauth_client_id,
        issuer=ISSUER,
    )
    return claims
