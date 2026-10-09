"""
Оплата картой (рубли).

Robokassa удалена полностью (ADR-022): её клиент, подпись, вебхук и
гостевой чекаут больше не существуют. Новый эквайринг ещё не подключён,
поэтому card_ready() возвращает False — бот, сайт и админка показывают
«Оплату картой» недоступной. Рублёвые цены остаются: их показывает сайт,
по ним будет работать новый провайдер. Подключая его, реализуйте здесь
создание ссылки на оплату и проверку вебхука, а card_ready() — по
наличию ключей в .env.
"""

from decimal import Decimal

CARD_PLANS: dict[str, dict] = {
    "plan_1m": {"days": 30, "rub": Decimal(199), "label": "1 месяц", "desc": "30 дней · 199 ₽"},
    "plan_3m": {"days": 90, "rub": Decimal(499), "label": "3 месяца",
                "desc": "90 дней · 499 ₽ · скидка 16%"},
    "plan_6m": {"days": 180, "rub": Decimal(899), "label": "6 месяцев",
                "desc": "180 дней · 899 ₽ · скидка 25%"},
}

# Произвольный срок (слайдер на /tariffs и /get-vpn) — только картой.
# Цена за день падает со сроком: 7-29 дней по 7 ₽, 30-89 по 6.6 ₽, 90-179
# по 5.5 ₽, 180 — по 5 ₽ (по краям совпадает с фиксированными тарифами).
CUSTOM_DAYS_MIN = 7
CUSTOM_DAYS_MAX = 180


def custom_day_rate(days: int) -> Decimal:
    if days >= 180:
        return Decimal(5)
    if days >= 90:
        return Decimal("5.5")
    if days >= 30:
        return Decimal("6.6")
    return Decimal(7)


def custom_plan_price(days: int) -> Decimal:
    """Итоговая цена в рублях за произвольный срок, округлённая до рубля."""
    return (Decimal(days) * custom_day_rate(days)).quantize(Decimal(1))


def card_ready() -> bool:
    """Можно ли сейчас принять оплату картой. Провайдера нет — нельзя."""
    return False
