"""
Брендирование VLESS-ссылок.

Marzban отдаёт ссылку с remark на основе marzban_username — в клиенте это
выглядит как технический идентификатор. set_vless_remark подменяет его на
«STAR VPN», и делать это нужно одинаково во всех точках выдачи ключа
(бот, мини-апп, дашборд, профиль).
"""

import urllib.parse

import pytest

from bot.utils.branding import APP_NAME, set_vless_remark, set_vless_remark_text

LINK = "vless://uuid-1234@example.com:443?security=reality&sni=a.com"


def test_adds_remark_when_link_has_none():
    assert set_vless_remark(LINK) == f"{LINK}#{urllib.parse.quote(APP_NAME)}"


def test_replaces_existing_technical_remark():
    """Ключевой случай: в ссылке от Marzban уже есть #tg_12345."""
    result = set_vless_remark(f"{LINK}#tg_12345")
    assert "tg_12345" not in result
    assert result.endswith(urllib.parse.quote(APP_NAME))


def test_device_label_is_used_when_known():
    result = set_vless_remark(LINK, "ios")
    assert urllib.parse.unquote(result.split("#", 1)[1]) == f"{APP_NAME} · iPhone"


def test_unknown_device_falls_back_to_app_name():
    result = set_vless_remark(LINK, "nokia3310")
    assert urllib.parse.unquote(result.split("#", 1)[1]) == APP_NAME


def test_remark_is_url_encoded():
    """Пробелы и · обязаны быть закодированы, иначе клиент рвёт ссылку."""
    result = set_vless_remark(LINK, "androidtv")
    assert " " not in result.split("#", 1)[1]


def test_custom_remark_text():
    assert set_vless_remark_text(f"{LINK}#old", "Мой ключ").endswith(
        urllib.parse.quote("Мой ключ")
    )


@pytest.mark.parametrize("empty", ["", None])
def test_empty_link_passes_through(empty):
    assert set_vless_remark(empty) == empty
