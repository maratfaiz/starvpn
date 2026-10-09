"""
Настройки сервиса, которые владелец меняет в /admin → Настройки (ADR-022).

Хранятся в app_settings (ключи "cfg.*"), кэшируются в памяти процесса —
бот и API живут в одном процессе (как bot_texts и admin_auth): load_cache
на старте, save() из админки сразу обновляет кэш. Без записей в БД всё
работает как раньше: значения по умолчанию — те, что были в коде и .env.

Цены тарифов применяются прямо к STARS_PLANS / CRYPTO_PLANS / CARD_PLANS —
их импортируют бот, сайт и Mini App, поэтому новая цена видна везде сразу.
"""

import copy
import re
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.app_setting import AppSetting
from bot.utils.card import CARD_PLANS
from bot.utils.cryptopay import CRYPTO_PLANS
from bot.utils.plans import STARS_PLANS

PREFIX = "cfg."
PLAN_KEYS = tuple(STARS_PLANS)

# Цены «как в коде» — чтобы сброс настройки возвращал исходное значение.
_DEFAULT_PLANS = {
    "stars": copy.deepcopy(STARS_PLANS),
    "usd": copy.deepcopy(CRYPTO_PLANS),
    "rub": copy.deepcopy(CARD_PLANS),
}

# key → (тип, минимум, максимум, значение по умолчанию)
FIELDS: dict[str, tuple[str, float, float, object]] = {
    "trial_enabled": ("bool", 0, 1, True),
    "trial_days": ("int", 1, 30, settings.trial_days),
    "max_devices": ("int", 1, 10, 3),
    "referral_bonus_days": ("int", 0, 365, 30),
    "referral_milestone": ("int", 1, 50, 2),
    "tg_oauth_secret": ("secret", 0, 200, ""),
}
for _plan in PLAN_KEYS:
    FIELDS[f"price.stars.{_plan}"] = ("int", 1, 100000, _DEFAULT_PLANS["stars"][_plan]["stars"])
    FIELDS[f"price.usd.{_plan}"] = ("money", 0.1, 10000, _DEFAULT_PLANS["usd"][_plan]["usd"])
    FIELDS[f"price.rub.{_plan}"] = ("int", 1, 1000000, int(_DEFAULT_PLANS["rub"][_plan]["rub"]))

_values: dict[str, str] = {}


def _parse(key: str, raw: str) -> object:
    kind, lo, hi, _ = FIELDS[key]
    if kind == "bool":
        return raw == "1"
    if kind == "secret":
        return raw
    try:
        num = Decimal(raw) if kind == "money" else int(raw)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{key}: нужно число") from None
    if not lo <= num <= hi:
        raise ValueError(f"{key}: от {lo:g} до {hi:g}")
    return num.quantize(Decimal("0.01")) if kind == "money" else num


def get(key: str) -> object:
    raw = _values.get(key)
    if raw is None:
        return FIELDS[key][3]
    try:
        return _parse(key, raw)
    except ValueError:  # значение из старой версии вне допустимого — берём стандартное
        return FIELDS[key][3]


def is_overridden(key: str) -> bool:
    return key in _values


# ── Доступ из кода ────────────────────────────────────────────────────────────

def trial_enabled() -> bool:
    return bool(get("trial_enabled"))


def trial_days() -> int:
    return int(get("trial_days"))


def max_devices() -> int:
    return int(get("max_devices"))


def referral_bonus_days() -> int:
    return int(get("referral_bonus_days"))


def referral_milestone() -> int:
    return int(get("referral_milestone"))


def tg_oauth_client_id() -> str:
    """Client ID для входа через Telegram — это числовой ID бота. Если он не
    задан в .env, берём его из токена бота (часть до двоеточия)."""
    env = settings.telegram_oauth_client_id.strip()
    if env:
        return env
    head = settings.telegram_api_token.split(":", 1)[0]
    return head if head.isdigit() else ""


def tg_oauth_client_secret() -> str:
    """Client Secret: из админки, иначе из .env (TELEGRAM_OAUTH_CLIENT_SECRET)."""
    return str(get("tg_oauth_secret")).strip() or settings.telegram_oauth_client_secret.strip()


def _apply_prices() -> None:
    for plan in PLAN_KEYS:
        days = STARS_PLANS[plan]["days"]
        STARS_PLANS[plan]["stars"] = int(get(f"price.stars.{plan}"))
        usd = get(f"price.usd.{plan}")
        CRYPTO_PLANS[plan]["usd"] = usd
        CRYPTO_PLANS[plan]["desc"] = _desc(days, f"${usd}", _DEFAULT_PLANS["usd"][plan]["desc"])
        rub = Decimal(int(get(f"price.rub.{plan}")))
        CARD_PLANS[plan]["rub"] = rub
        CARD_PLANS[plan]["desc"] = _desc(days, f"{rub} ₽", _DEFAULT_PLANS["rub"][plan]["desc"])


def _desc(days: int, price: str, default: str) -> str:
    """«90 дней · 499 ₽ · скидка 16%» — скидка из исходного описания остаётся,
    только если цена не менялась (иначе процент был бы неправдой)."""
    base = f"{days} дней · {price}"
    discount = re.search(r" · скидка \d+%$", default)
    return base + discount.group(0) if discount and default.startswith(base) else base


# ── Загрузка и сохранение ─────────────────────────────────────────────────────

async def load_cache(session: AsyncSession) -> None:
    global _values
    rows = (await session.execute(
        select(AppSetting).where(AppSetting.key.startswith(PREFIX))
    )).scalars().all()
    _values = {r.key[len(PREFIX):]: r.value for r in rows if r.key[len(PREFIX):] in FIELDS}
    _apply_prices()


async def save(session: AsyncSession, changes: dict[str, object]) -> None:
    """changes: {key: значение | None}; None — вернуть значение по умолчанию.
    ValueError — с текстом для админки; при ошибке ничего не сохраняется."""
    rows: dict[str, str | None] = {}
    for key, value in changes.items():
        if key not in FIELDS:
            raise ValueError(f"Неизвестная настройка: {key}")
        if value is None or value == "":
            rows[key] = None
            continue
        raw = ("1" if value else "0") if FIELDS[key][0] == "bool" else str(value).strip()
        _parse(key, raw)
        rows[key] = raw

    existing = {
        r.key: r for r in (await session.execute(
            select(AppSetting).where(AppSetting.key.in_([PREFIX + k for k in rows]))
        )).scalars().all()
    }
    for key, raw in rows.items():
        row = existing.get(PREFIX + key)
        if raw is None:
            if row:
                await session.delete(row)
        elif row:
            row.value = raw
        else:
            session.add(AppSetting(key=PREFIX + key, value=raw))
    await session.commit()
    await load_cache(session)


def public_view() -> dict:
    """Текущие значения для админки — секрет не отдаём, только «задан/нет»."""
    out = {}
    for key, (kind, lo, hi, default) in FIELDS.items():
        value = get(key)
        if kind == "secret":
            value = bool(value)
            default = bool(default)
        elif kind == "money":
            value, default = float(value), float(default)
        out[key] = {"value": value, "default": default, "min": lo, "max": hi,
                    "type": kind, "overridden": is_overridden(key)}
    return out
