"""
Формат Marzban username — правило из CLAUDE.md, ломать его нельзя:
устройства ищутся в Marzban именно по этому имени.
"""

from bot.handlers.devices import _mz_username_for_type


def test_uses_telegram_username_when_present():
    assert _mz_username_for_type("ios", 12345, "MaratF", []) == "ios_tg_maratf"


def test_falls_back_to_telegram_id_without_username():
    assert _mz_username_for_type("ios", 12345, None, []) == "ios_tg_12345"


def test_suffix_added_on_collision():
    existing = ["ios_tg_12345"]
    assert _mz_username_for_type("ios", 12345, None, existing) == "ios2_tg_12345"


def test_walks_up_through_taken_suffixes():
    existing = ["ios_tg_12345"] + [f"ios{i}_tg_12345" for i in range(2, 5)]
    assert _mz_username_for_type("ios", 12345, None, existing) == "ios5_tg_12345"


def test_exhausted_suffixes_fall_back_to_id_form():
    existing = ["ios_tg_bob"] + [f"ios{i}_tg_bob" for i in range(2, 10)]
    assert _mz_username_for_type("ios", 999, "bob", existing) == "ios_tg_999"
