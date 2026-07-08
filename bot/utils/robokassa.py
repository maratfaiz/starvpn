"""
Оплата картой (рубли) через Robokassa.

Документация: https://docs.robokassa.ru/
Никаких HTTP-вызовов не требуется — платёж инициируется подписанной
ссылкой на страницу оплаты Robokassa, а подтверждение приходит через
ResultURL (server-to-server webhook).

Подпись ссылки (Index.aspx):      MD5(MerchantLogin:OutSum:InvId:Password#1)
Подпись ResultURL (входящая):     MD5(OutSum:InvId:Password#2)
"""

import hashlib
import logging
import urllib.parse
from decimal import Decimal

from bot.config import settings

logger = logging.getLogger(__name__)

ROBOKASSA_PAY_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"

# ─── Тарифы (цены в рублях) ───────────────────────────────────────────────────

CARD_PLANS: dict[str, dict] = {
    "plan_1m": {
        "days": 30,
        "rub": Decimal("199"),
        "label": "1 месяц",
        "desc": "30 дней · 199 ₽",
    },
    "plan_3m": {
        "days": 90,
        "rub": Decimal("499"),
        "label": "3 месяца",
        "desc": "90 дней · 499 ₽ · скидка 16%",
    },
    "plan_6m": {
        "days": 180,
        "rub": Decimal("899"),
        "label": "6 месяцев",
        "desc": "180 дней · 899 ₽ · скидка 25%",
    },
}


class Robokassa:
    """Тонкий клиент для Robokassa: строит подписанные ссылки и проверяет
    подпись входящего ResultURL. Никакого состояния — все данные о
    платеже (сумма, план) хранятся в нашей таблице Payment по InvId."""

    def __init__(self) -> None:
        self._login = settings.robokassa_merchant_id
        self._password1 = settings.robokassa_password1
        self._password2 = settings.robokassa_password2
        self._test_mode = settings.robokassa_test_mode

    @property
    def configured(self) -> bool:
        return bool(self._login and self._password1)

    def build_payment_url(self, inv_id: int, amount: Decimal | str, description: str) -> str:
        if not self.configured:
            raise RuntimeError("ROBOKASSA_MERCHANT_ID / ROBOKASSA_PASSWORD1 не заданы в .env")

        out_sum = f"{Decimal(amount):.2f}"
        signature = hashlib.md5(
            f"{self._login}:{out_sum}:{inv_id}:{self._password1}".encode()
        ).hexdigest()

        params = {
            "MerchantLogin": self._login,
            "OutSum": out_sum,
            "InvId": inv_id,
            "Description": description,
            "SignatureValue": signature,
            "Culture": "ru",
        }
        if self._test_mode:
            params["IsTest"] = 1

        return f"{ROBOKASSA_PAY_URL}?{urllib.parse.urlencode(params)}"

    def check_result_signature(self, out_sum: str, inv_id: str, signature: str) -> bool:
        """Проверка подписи ResultURL: MD5(OutSum:InvId:Password#2)."""
        if not self._password2:
            return False
        expected = hashlib.md5(f"{out_sum}:{inv_id}:{self._password2}".encode()).hexdigest()
        return expected.lower() == signature.lower()


# Глобальный синглтон — используется в handlers и api.py
robokassa = Robokassa()
