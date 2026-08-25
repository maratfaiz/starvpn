"""
Общая настройка тестов.

bot.config.Settings читает обязательные переменные окружения при импорте
любого модуля бота, поэтому подставляем фиктивные значения ДО импорта —
иначе `import bot.api` падает ещё на этапе сбора тестов.
"""

import os

os.environ.setdefault("TELEGRAM_API_TOKEN", "123456:TEST-TOKEN-FOR-PYTEST")
os.environ.setdefault("TELEGRAM_ADMIN_ID", "1")
# Движок создаётся при импорте bot.utils.database, но к базе не подключается,
# поэтому достаточно синтаксически валидного DSN — сервер не нужен.
os.environ.setdefault(
    "SQLALCHEMY_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test"
)
