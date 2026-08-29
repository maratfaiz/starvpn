"""Название устройства, которое вводит пользователь.

Тип устройства выбирается из фиксированного списка, а имя пишет человек,
поэтому его нужно обрезать по длине колонки и подставлять осмысленное
значение по умолчанию, когда поле оставили пустым.
"""

import pytest

from bot.api import DEVICE_NAME_MAX, DEVICE_TYPE_LABELS, DEVICE_TYPES_API, _clean_device_name


def test_uses_typed_name():
    assert _clean_device_name("Телефон Марата", "ios") == "Телефон Марата"


def test_trims_surrounding_whitespace():
    assert _clean_device_name("  MacBook  ", "macos") == "MacBook"


@pytest.mark.parametrize("empty", ["", "   ", None, 123, [], {}])
def test_falls_back_to_type_label(empty):
    """Пустое, отсутствующее или не-строковое поле → ярлык типа."""
    assert _clean_device_name(empty, "androidtv") == "Смарт-ТВ"


def test_truncates_to_column_width():
    """devices.name — VARCHAR(64): более длинное имя уронило бы вставку."""
    result = _clean_device_name("я" * 300, "ios")
    assert len(result) == DEVICE_NAME_MAX


def test_every_api_type_has_a_default_label():
    """Иначе устройство без имени называлось бы техническим ключом."""
    assert set(DEVICE_TYPE_LABELS) == DEVICE_TYPES_API


def test_unknown_type_falls_back_to_the_key():
    """Тип валидируется до этого места, но помощник не должен падать."""
    assert _clean_device_name("", "nokia3310") == "nokia3310"
