"""
Оплата картой / СБП / из кошелька через ЮMoney Quickpay — второй рублёвый
рельс в резерв на случай проблем с Robokassa. Паспорт не требуется ни в
одном из способов оплаты на стороне ЮMoney.

Формирование ссылки:  https://yoomoney.ru/docs/wallet/process-payments/quickpay/forms
                       GET/POST на https://yoomoney.ru/quickpay/confirm.xml,
                       подписи не требует — сумма и получатель наши.
HTTP-уведомления:      https://yoomoney.ru/docs/wallet/using-api/notification-p2p-incoming
                       Подпись `sign`: HMAC-SHA256(secret, "k1=v1&k2=v2&..."),
                       параметры отсортированы по ключу (кроме sign), значения
                       URL-encoded (UTF-8, RFC 3986).
"""

import hashlib
import hmac
import logging
import urllib.parse
from decimal import Decimal

from bot.config import settings
from bot.utils.robokassa import CARD_PLANS  # те же тарифы, что и у Robokassa

logger = logging.getLogger(__name__)

QUICKPAY_URL = "https://yoomoney.ru/quickpay/confirm.xml"

__all__ = ["CARD_PLANS", "YooMoney", "yoomoney", "payment_label", "guest_label", "decode_label"]


class YooMoney:
    """Строит ссылки на оплату через Quickpay и проверяет подпись входящих
    HTTP-уведомлений о зачислении. Никакого состояния — данные о платеже
    (сумма, план) хранятся в наших таблицах Payment/GuestOrder по label."""

    def __init__(self) -> None:
        self._receiver = settings.yoomoney_wallet
        self._secret = settings.yoomoney_notification_secret

    @property
    def configured(self) -> bool:
        return bool(self._receiver and self._secret)

    def build_payment_url(self, label: str, amount: Decimal | str, description: str, success_url: str = "") -> str:
        if not self.configured:
            raise RuntimeError("YOOMONEY_WALLET / YOOMONEY_NOTIFICATION_SECRET не заданы в .env")

        params = {
            "receiver": self._receiver,
            "quickpay-form": "shop",
            "targets": description,
            "sum": f"{Decimal(amount):.2f}",
            "label": label,
        }
        if success_url:
            params["successURL"] = success_url

        return f"{QUICKPAY_URL}?{urllib.parse.urlencode(params)}"

    def check_notification_signature(self, params: dict) -> bool:
        """Проверка подписи `sign` из HTTP-уведомления о зачислении."""
        if not self._secret:
            return False
        received = params.get("sign", "")
        if not received:
            return False

        items = sorted((k, v) for k, v in params.items() if k != "sign")
        message = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in items)
        expected = hmac.new(self._secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, received.lower())


# Глобальный синглтон — используется в handlers и api.py
yoomoney = YooMoney()


# ─── label — идентификатор платежа, передаётся ЮMoney насквозь и возвращается
#     в уведомлении. В отличие от Robokassa InvId это произвольная строка,
#     поэтому Payment/GuestOrder кодируются префиксом, а не чётностью.

def payment_label(payment_id: int) -> str:
    return f"pay{payment_id}"


def guest_label(guest_order_id: int) -> str:
    return f"guest{guest_order_id}"


def decode_label(label: str) -> tuple[str, int]:
    """Возвращает ("payment" | "guest", исходный id строки в таблице)."""
    if label.startswith("guest"):
        return "guest", int(label[len("guest"):])
    if label.startswith("pay"):
        return "payment", int(label[len("pay"):])
    raise ValueError(f"Неизвестный формат label: {label!r}")
