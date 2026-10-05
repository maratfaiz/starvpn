"""Баннер на верхней полосе сайта (/admin → Баннер): иконки и оформления.

Единственный источник правды: сайт и админка получают пути иконок и цвета
оформлений из API (/api/ad-banner, /web/ad-banner), своих копий у них нет.
Иконки — фиксированный набор SVG-путей (viewBox 0 0 24 24, fill-rule
evenodd), а не произвольный SVG от админа: так в баннер не пронести XSS.
Своя иконка — картинка, загруженная через /web/media (AdBanner.icon_media_id).
"""

import re
from datetime import datetime, timezone

# ключ → (подпись, SVG path)
BANNER_ICONS: dict[str, tuple[str, str]] = {
    "sparkle": ("Искра", "M12 2l1.5 6.5L20 10l-6.5 1.5L12 18l-1.5-6.5L4 10l6.5-1.5z"),
    "star": ("Звезда", ("M12 2L14.64 8.36L21.51 8.91L16.28 13.39L17.88 20.09L12 16.5L6.12 20.09"
              "L7.72 13.39L2.49 8.91L9.36 8.36Z")),
    "fire": ("Огонь", ("M12 2c1 3-3 4-3 8a3 3 0 006 0c0-2-1-2-1-4 2 1 3 3 3 6a5 5 0 01-10 0"
              "c0-5 3-6 5-10z")),
    "gift": ("Подарок", ("M4 11h7v10H4zM13 11h7v10h-7zM3 8h8v3H3zM13 8h8v3h-8zM8.5 4a2 2 0 100 4"
              "h2v-2a2 2 0 00-2-2zm7 0a2 2 0 010 4h-2v-2a2 2 0 012-2z")),
    "percent": ("Скидка", ("M6 6a2.5 2.5 0 100 5 2.5 2.5 0 000-5zm12 7a2.5 2.5 0 100 5 2.5 2.5 0 "
                 "000-5zM17.5 5.5l-11 13 1.5 1.5 11-13z")),
    "tag": ("Ценник", "M3 3h8l10 10-8 8L3 11zm4.5 2.5a2 2 0 100 4 2 2 0 000-4z"),
    "ticket": ("Промокод", ("M3 6h18v4a2 2 0 000 4v4H3v-4a2 2 0 000-4zm10 2v2h2V8zm0 3v2h2v-2z"
                "m0 3v2h2v-2z")),
    "bell": ("Колокол", ("M12 2a1 1 0 011 1v1.06a8 8 0 016 7.74v3l1.6 2.4a1 1 0 01-.83 1.55H5.23"
              "a1 1 0 01-.83-1.55L6 14.8v-3a8 8 0 016-7.74V3a1 1 0 011-1zM9.5 20a2.5 2.5 0 005 0z")),
    "megaphone": ("Рупор", "M3 10v4a1 1 0 001 1h2l1 5h3l-1-5h1l9 5V4l-9 5H4a1 1 0 00-1 1z"),
    "rocket": ("Ракета", ("M12 2c3 2.5 4 6.5 4 9.5 0 2-.7 3.8-1.8 5.1l.3 4.4-2.5-2-2.5 2 .3-4.4"
                "C8.7 15.3 8 13.5 8 11.5 8 8.5 9 4.5 12 2zm0 6a2 2 0 100 4 2 2 0 000-4zM6.5 15"
                "l-2 5 4-3zM17.5 15l2 5-4-3z")),
    "zap": ("Молния", "M13 2L3 14h6l-1 8 11-13h-6z"),
    "shield": ("Защита", ("M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5zm-1.2 13.6L17 9.4 15.6 8"
                "l-4.8 4.8-2.4-2.4L7 11.8z")),
    "lock": ("Замок", ("M7 10V7a5 5 0 0110 0v3h1a1 1 0 011 1v10a1 1 0 01-1 1H6a1 1 0 01-1-1V11"
              "a1 1 0 011-1zm2 0h6V7a3 3 0 00-6 0z")),
    "crown": ("Корона", "M3 7l4.5 4L12 4l4.5 7L21 7l-2 12H5z"),
    "trophy": ("Кубок", ("M6 3h12v5a6 6 0 01-5 5.9V17h3v3H8v-3h3v-3.1A6 6 0 016 8zM2 5h3v2H4v1"
                "a2 2 0 001 1.7v2.1A4 4 0 012 8zM22 5h-3v2h1v1a2 2 0 01-1 1.7v2.1A4 4 0 0022 8z")),
    "diamond": ("Бриллиант", "M6 3h12l4 6-10 12L2 9z"),
    "heart": ("Сердце", ("M12 21s-7-4.6-9.3-9.1C1.4 9 2.6 5.8 5.6 5c2-.5 3.8.3 4.9 1.9C11.6 5.3 "
               "13.4 4.5 15.4 5c3 .8 4.2 4 3 6.9C16 16.4 12 21 12 21z")),
    "smile": ("Улыбка", ("M12 2a10 10 0 110 20 10 10 0 010-20zM8.5 8a1.5 1.5 0 100 3 1.5 1.5 0 "
               "000-3zm7 0a1.5 1.5 0 100 3 1.5 1.5 0 000-3zM7 14a5 5 0 0010 0z")),
    "users": ("Друзья", ("M9 11a4 4 0 100-8 4 4 0 000 8zm-7 9a7 7 0 0114 0v1H2zm14.5-9a3.5 3.5 0 "
               "100-7 3.5 3.5 0 000 7zm1.5 2a6 6 0 015 6v2h-4v-1a8.9 8.9 0 00-2.4-6.1z")),
    "chat": ("Сообщение", ("M4 3h16a2 2 0 012 2v11a2 2 0 01-2 2H9l-5 4v-4a2 2 0 01-2-2V5a2 2 0 "
              "012-2z")),
    "send": ("Telegram", "M2 21l21-9L2 3v7l15 2-15 2z"),
    "pin": ("Локация", ("M12 2a7 7 0 017 7c0 5-7 13-7 13S5 14 5 9a7 7 0 017-7zm0 4.5a2.5 2.5 0 "
             "100 5 2.5 2.5 0 000-5z")),
    "calendar": ("Календарь", ("M7 2h2v2h6V2h2v2h2a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V6"
                  "a2 2 0 012-2h2zM5 9v11h14V9zm2 2h4v4H7z")),
    "clock": ("Часы", "M12 2a10 10 0 100 20 10 10 0 000-20zm1 5v5.5l4 2.3-1 1.7-5-3V7z"),
    "sun": ("Солнце", ("M12 7a5 5 0 110 10 5 5 0 010-10zM11 1h2v3h-2zM11 20h2v3h-2zM1 11h3v2H1z"
             "M20 11h3v2h-3zM4.2 5.6l1.4-1.4 2.1 2.1-1.4 1.4zM16.3 17.7l1.4-1.4 2.1 2.1-1.4 1.4z"
             "M4.2 18.4l2.1-2.1 1.4 1.4-2.1 2.1zM16.3 6.3l2.1-2.1 1.4 1.4-2.1 2.1z")),
    "info": ("Инфо", "M12 2a10 10 0 110 20 10 10 0 010-20zm-1 8v7h2v-7zm0-4v2h2V6z"),
    "check": ("Готово", ("M12 2a10 10 0 110 20 10 10 0 010-20zm-1.2 13.6L17 9.4 15.6 8l-4.8 4.8"
               "-2.4-2.4L7 11.8z")),
}

# ключ → подпись и CSS-значения (фон может быть градиентом)
BANNER_STYLES: dict[str, dict[str, str]] = {
    "gold": {"label": "Золотой", "bg": "rgba(255,184,0,.09)", "border": "rgba(255,184,0,.22)",
             "text": "#F0E6D2", "accent": "#FFB800"},
    "solid": {"label": "Яркий", "bg": "linear-gradient(90deg,#FFB800,#FF8A00)",
              "border": "rgba(0,0,0,0)", "text": "#1A1000", "accent": "#1A1000"},
    "dark": {"label": "Тёмный", "bg": "#0D0B08", "border": "rgba(255,255,255,.08)",
             "text": "#E8DCC4", "accent": "#FFB800"},
    "green": {"label": "Зелёный", "bg": "rgba(52,211,153,.1)", "border": "rgba(52,211,153,.25)",
              "text": "#E6F7EF", "accent": "#34D399"},
    "blue": {"label": "Синий", "bg": "rgba(96,165,250,.1)", "border": "rgba(96,165,250,.25)",
             "text": "#E8F1FF", "accent": "#60A5FA"},
    "purple": {"label": "Неон",
               "bg": "linear-gradient(90deg,rgba(139,92,246,.28),rgba(236,72,153,.22))",
               "border": "rgba(167,139,250,.3)", "text": "#F3EEFF", "accent": "#D8B4FE"},
    "sale": {"label": "Распродажа", "bg": "linear-gradient(90deg,#7F1D1D,#B91C1C)",
             "border": "rgba(0,0,0,0)", "text": "#FFF1F1", "accent": "#FFD166"},
}

# https://… или путь на этом сайте (/tariffs). Не //host и не javascript:.
_LINK_RE = re.compile(r"^(https?://[^\s\"'<>]+|/(?!/)[^\s\"'<>]*)$")


def valid_link(url: str) -> bool:
    return bool(_LINK_RE.match(url)) and len(url) <= 500


def style_css(key: str) -> dict[str, str]:
    s = BANNER_STYLES.get(key) or BANNER_STYLES["gold"]
    return {k: v for k, v in s.items() if k != "label"}


def icon_path(key: str) -> str:
    return (BANNER_ICONS.get(key) or BANNER_ICONS["sparkle"])[1]


def parse_dt(value: str | None) -> datetime | None:
    """ISO-время из админки (с часовым поясом браузера) → наивное UTC, как в БД."""
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def iso_utc(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def status(banner, now: datetime | None = None) -> str:
    """off | empty | scheduled | ended | live"""
    now = now or datetime.utcnow()
    if not banner.enabled:
        return "off"
    if not (banner.text or "").strip():
        return "empty"
    if banner.starts_at and now < banner.starts_at:
        return "scheduled"
    if banner.ends_at and now >= banner.ends_at:
        return "ended"
    return "live"
