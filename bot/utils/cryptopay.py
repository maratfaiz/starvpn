"""
Async-клиент для Crypto Pay API (@CryptoBot).

Документация: https://help.crypt.bot/crypto-pay-api

Создаём fiat-инвойс в USD — пользователь сам выбирает
криптовалюту (USDT / TON / BTC / ETH) внутри @CryptoBot.
"""

import hashlib
import hmac
import logging
from decimal import Decimal

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)

CRYPTOPAY_API = "https://pay.crypt.bot/api"

# ─── Тарифы (цены в USD) ─────────────────────────────────────────────────────

CRYPTO_PLANS: dict[str, dict] = {
    "plan_1m": {
        "days": 30,
        "usd": Decimal("1.50"),
        "label": "1 месяц",
        "desc": "30 дней · $1.50",
    },
    "plan_3m": {
        "days": 90,
        "usd": Decimal("3.99"),
        "label": "3 месяца",
        "desc": "90 дней · $3.99 · скидка 11%",
    },
    "plan_6m": {
        "days": 180,
        "usd": Decimal("6.99"),
        "label": "6 месяцев",
        "desc": "180 дней · $6.99 · скидка 22%",
    },
}


# ─── CryptoPay клиент ─────────────────────────────────────────────────────────

class CryptoPay:
    """Тонкий async-клиент для Crypto Pay API."""

    def __init__(self) -> None:
        self._token: str = settings.cryptopay_token

    @property
    def _headers(self) -> dict[str, str]:
        return {"Crypto-Pay-API-Token": self._token}

    async def create_invoice(
        self,
        usd_amount: Decimal | str,
        payload: str,
        description: str = "STAR VPN",
    ) -> dict:
        """
        Создаёт счёт с ценой в USD.
        Пользователь выбирает USDT / TON / BTC / ETH в боте @CryptoBot.

        Returns:
            dict с полями: invoice_id, bot_invoice_url, pay_url, status, ...
        """
        if not self._token:
            raise RuntimeError("CRYPTOPAY_TOKEN не задан в .env")

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{CRYPTOPAY_API}/createInvoice",
                headers=self._headers,
                json={
                    "currency_type": "fiat",
                    "fiat": "USD",
                    "amount": str(usd_amount),
                    "accepted_assets": "USDT,TON,BTC,ETH",
                    "payload": payload,
                    "description": description,
                    "paid_btn_name": "openBot",
                    "paid_btn_url": f"https://t.me/{settings.bot_username}",
                    "expires_in": 3600,  # 1 час
                },
            )

        data = r.json()
        if not data.get("ok"):
            error = data.get("error", {})
            raise RuntimeError(f"CryptoPay API error: {error}")
        return data["result"]

    def check_signature(self, body: str | bytes, signature: str) -> bool:
        """
        Проверяет подпись входящего вебхука от CryptoPay.
        Алгоритм: HMAC-SHA256(key=SHA256(token), data=body_string)
        """
        if not self._token:
            return False
        if isinstance(body, str):
            body = body.encode()
        secret = hashlib.sha256(self._token.encode()).digest()
        computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature.lower())


# Глобальный синглтон — используется в handlers и api.py
cryptopay = CryptoPay()
