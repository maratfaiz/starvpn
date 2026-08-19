"""
Включение/выключение способов оплаты из админ-панели.

Stars не тумблится — это нативная валюта Telegram, всегда доступна в боте
бесплатно для нас (комиссии нет), выключать её незачем. Card/ЮMoney/Crypto
тумблятся независимо; по умолчанию (нет строки в БД) — включены, чтобы
поведение не менялось, пока админ ничего не трогал.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.app_setting import AppSetting

PROVIDER_KEYS = {
    "card": "payment_card_enabled",
    "yoomoney": "payment_yoomoney_enabled",
    "crypto": "payment_crypto_enabled",
}


async def is_provider_enabled(session: AsyncSession, provider: str) -> bool:
    key = PROVIDER_KEYS.get(provider)
    if not key:
        return True
    row = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = row.scalar_one_or_none()
    if setting is None:
        return True
    return setting.value == "1"


async def set_provider_enabled(session: AsyncSession, provider: str, enabled: bool) -> None:
    key = PROVIDER_KEYS.get(provider)
    if not key:
        raise ValueError(f"Unknown provider: {provider}")
    row = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = row.scalar_one_or_none()
    if setting:
        setting.value = "1" if enabled else "0"
    else:
        session.add(AppSetting(key=key, value="1" if enabled else "0"))
    await session.commit()


async def get_all_provider_states(session: AsyncSession) -> dict[str, bool]:
    return {p: await is_provider_enabled(session, p) for p in PROVIDER_KEYS}
