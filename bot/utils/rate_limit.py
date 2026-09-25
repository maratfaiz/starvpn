"""Простой счётчик неудачных попыток в памяти процесса — от перебора паролей.

Ключ — логин/email, а не IP: IP-адреса пользователей не храним нигде (Zero
Logs, см. CLAUDE.md). После MAX_FAILS неудач подряд за WINDOW вход по этому
ключу закрыт до конца окна; успешный вход сбрасывает счётчик.
"""

import time

MAX_FAILS = 10
WINDOW = 15 * 60  # секунд

_fails: dict[str, list[float]] = {}


def _recent(key: str) -> list[float]:
    now = time.monotonic()
    hits = [t for t in _fails.get(key, []) if now - t < WINDOW]
    if hits:
        _fails[key] = hits
    else:
        _fails.pop(key, None)
    return hits


def is_blocked(key: str) -> bool:
    return len(_recent(key)) >= MAX_FAILS


def register_fail(key: str) -> None:
    _recent(key)
    _fails.setdefault(key, []).append(time.monotonic())


def reset(key: str) -> None:
    _fails.pop(key, None)
