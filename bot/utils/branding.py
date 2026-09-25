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

import hashlib
import hmac
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


def _sub_signature(marzban_username: str) -> str:
    from bot.config import settings
    key = hashlib.sha256(b"sub-link:" + settings.telegram_api_token.encode()).digest()
    return hmac.new(key, marzban_username.encode(), hashlib.sha256).hexdigest()[:24]


def check_sub_signature(marzban_username: str, signature: str) -> bool:
    return hmac.compare_digest(_sub_signature(marzban_username), signature or "")


def subscription_url(marzban_username: str) -> str:
    """
    URL подписки (GET /sub/{username}/{подпись} в api.py) — рекомендуемый
    способ добавить STAR VPN в Happ: даёт название "STAR VPN", живой
    счётчик трафика и сообщение об истечении подписки вместо обрыва.

    Подпись обязательна: имя пользователя в Marzban предсказуемо
    (ios_tg_<@username>), и без неё любой мог открыть /sub/… и забрать
    чужой VLESS-ключ.
    """
    from bot.config import settings
    base = (settings.webapp_url or settings.site_url).rstrip("/")
    return f"{base}/sub/{marzban_username}/{_sub_signature(marzban_username)}"


# Имя бота и аккаунт поддержки, под которыми свёрстаны страницы сайта и
# базовые статьи Wiki. При отдаче страницы они заменяются на BOT_USERNAME и
# SUPPORT_USERNAME из .env — чтобы на новом проекте не приходилось править
# десятки HTML-файлов и все ссылки вели на свой бот.
_TEMPLATE_BOT = "starisvpnbot"
_TEMPLATE_SUPPORT = "hashprojects"


def brand_html(page: str) -> str:
    from bot.config import settings
    bot = settings.bot_username.lstrip("@")
    support = settings.support_username.lstrip("@")
    if bot and bot != _TEMPLATE_BOT:
        page = page.replace(_TEMPLATE_BOT, bot)
    if support and support != _TEMPLATE_SUPPORT:
        page = page.replace(_TEMPLATE_SUPPORT, support)
    return page
