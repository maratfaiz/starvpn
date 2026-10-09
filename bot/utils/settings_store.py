"""
Включение/выключение способов оплаты из админ-панели.

Card/Crypto/Stars тумблятся независимо через app_settings. Второй
рублёвый провайдер, который здесь раньше стоял рядом с card, был
удалён насовсем (ADR-015) — не только выключен тумблером, а полностью
убран из кода, конфигурации и админ-панели; если понадобится другой
рублёвый рельс, его нужно строить заново, а не искать старую
реализацию в git blame.

Card — «Оплата картой». Её провайдер (Robokassa) удалён (ADR-022), новый
ещё не подключён: пока bot.utils.card.card_ready() == False, card считается
выключенной везде, где бы ни стоял тумблер, и включить её нельзя.

Card и Crypto по умолчанию ВКЛЮЧЕНЫ, дефолт в коде важен только для
СВЕЖЕГО деплоя без строки в app_settings; если на проде тумблер уже
переключали руками через /admin, дефолт из кода его не перезапишет.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.app_setting import AppSetting
from bot.utils.card import card_ready

PROVIDER_KEYS = {
    "card": "payment_card_enabled",
    "crypto": "payment_crypto_enabled",
    "stars": "payment_stars_enabled",
}

_DEFAULT_ENABLED = {
    "card": True,
    "crypto": True,
    "stars": True,
}


async def is_provider_enabled(session: AsyncSession, provider: str) -> bool:
    if provider == "card" and not card_ready():
        return False
    key = PROVIDER_KEYS.get(provider)
    if not key:
        return True
    row = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = row.scalar_one_or_none()
    if setting is None:
        return _DEFAULT_ENABLED.get(provider, True)
    return setting.value == "1"


async def set_provider_enabled(session: AsyncSession, provider: str, enabled: bool) -> None:
    key = PROVIDER_KEYS.get(provider)
    if not key:
        raise ValueError(f"Unknown provider: {provider}")
    if provider == "card" and enabled and not card_ready():
        raise ValueError("Оплата картой не подключена")
    row = await session.execute(select(AppSetting).where(AppSetting.key == key))
    setting = row.scalar_one_or_none()
    if setting:
        setting.value = "1" if enabled else "0"
    else:
        session.add(AppSetting(key=key, value="1" if enabled else "0"))
    await session.commit()


async def get_all_provider_states(session: AsyncSession) -> dict[str, bool]:
    return {p: await is_provider_enabled(session, p) for p in PROVIDER_KEYS}
