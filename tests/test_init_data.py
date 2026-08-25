"""
Проверка Telegram initData: подпись + срок жизни.

Срок жизни (auth_date) важен отдельно от подписи: HMAC от Telegram
бессрочен, поэтому без проверки возраста перехваченная строка initData
работала бы вечно.
"""

import hashlib
import hmac
import json
import time
import urllib.parse

import pytest
from fastapi import HTTPException

from bot.api import INIT_DATA_MAX_AGE, _check_init_data_age, _parse_tg_id
from bot.config import settings


def _make_init_data(tg_id: int = 42, auth_date: int | None = None) -> str:
    """Собирает валидно подписанную строку initData, как её шлёт Telegram."""
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAF_test",
        "user": json.dumps({"id": tg_id, "first_name": "Test"}, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", settings.telegram_api_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)


def test_valid_init_data_returns_telegram_id():
    assert _parse_tg_id(_make_init_data(tg_id=777)) == 777


def test_tampered_signature_is_rejected():
    init_data = _make_init_data(tg_id=1)
    tampered = init_data.replace("first_name", "firstXname")
    with pytest.raises(HTTPException) as exc:
        _parse_tg_id(tampered)
    assert exc.value.status_code == 403


def test_expired_init_data_is_rejected():
    """Подпись верная, но auth_date старше окна — replay должен отлетать."""
    stale = int(time.time() - INIT_DATA_MAX_AGE.total_seconds() - 60)
    with pytest.raises(HTTPException) as exc:
        _parse_tg_id(_make_init_data(auth_date=stale))
    assert exc.value.status_code == 403
    assert "expired" in exc.value.detail


def test_init_data_just_inside_window_is_accepted():
    fresh_enough = int(time.time() - INIT_DATA_MAX_AGE.total_seconds() + 300)
    assert _parse_tg_id(_make_init_data(tg_id=9, auth_date=fresh_enough)) == 9


@pytest.mark.parametrize("bad", [None, "", "not-a-number"])
def test_missing_or_malformed_auth_date_is_rejected(bad):
    with pytest.raises(HTTPException) as exc:
        _check_init_data_age(bad)
    assert exc.value.status_code == 403


def test_future_auth_date_is_accepted():
    """Часы клиента могут немного убежать вперёд — это не replay."""
    _check_init_data_age(str(int(time.time()) + 120))
