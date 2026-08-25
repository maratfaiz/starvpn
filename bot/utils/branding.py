"""
Единое название "STAR VPN" в клиентах (Happ, Streisand, v2rayNG, ...).

VLESS-ссылки, которые отдаёт Marzban по умолчанию, используют remark
(#...) на основе marzban_username — в приложении это выглядит как
случайный технический идентификатор вместо названия сервиса. Эта
функция всегда используется перед тем, как показать ссылку/QR
пользователю — раньше так делал только один из способов получить
ключ (мини-апп), из-за чего в остальных (бот, дашборд, профиль) в
Happ отображался marzban_username вместо "STAR VPN".
"""

import urllib.parse

APP_NAME = "STAR VPN"

DEVICE_LABELS: dict[str, str] = {
    "ios":       f"{APP_NAME} · iPhone",
    "android":   f"{APP_NAME} · Android",
    "macos":     f"{APP_NAME} · macOS",
    "windows":   f"{APP_NAME} · Windows",
    "linux":     f"{APP_NAME} · Linux",
    "androidtv": f"{APP_NAME} · Смарт-ТВ",
    "appletv":   f"{APP_NAME} · Apple TV",
}

EXPIRED_REMARK = "⚠️ Подписка закончилась — продли в @{bot_username}"


def set_vless_remark(link: str, device_name: str | None = None) -> str:
    """Заменяет remark (#...) в VLESS-ссылке на брендированное название."""
    if not link:
        return link
    label = DEVICE_LABELS.get(device_name, APP_NAME) if device_name else APP_NAME
    if "#" in link:
        link = link[:link.index("#")]
    return f"{link}#{urllib.parse.quote(label)}"


def set_vless_remark_text(link: str, remark: str) -> str:
    """Как set_vless_remark, но с произвольным (уже готовым) текстом remark."""
    if not link:
        return link
    if "#" in link:
        link = link[:link.index("#")]
    return f"{link}#{urllib.parse.quote(remark)}"


def subscription_url(marzban_username: str) -> str:
    """
    URL подписки (GET /sub/{username} в api.py) — рекомендуемый способ
    добавить STAR VPN в Happ: даёт название "STAR VPN", живой счётчик
    трафика и сообщение об истечении подписки вместо простого обрыва.
    """
    from bot.config import settings
    return f"{settings.webapp_url.rstrip('/')}/sub/{marzban_username}"
