"""Отделяет тип устройства от его названия.

`devices.name` задумывалась как человеческое имя ("iPhone 15" — так и
записано в комментарии модели), но во всех местах создания устройства
туда клали технический ключ типа: "ios", "macos", "androidtv". Из-за
этого назвать устройство было негде.

Тип переезжает в отдельную колонку `device_type`, а `name` становится
тем, чем задумывалась. Существующие строки переносим: тип копируем
как есть, а в имя кладём человеческий ярлык этого типа — так список
устройств у текущих пользователей остаётся осмысленным.

Revision ID: 0008_device_name
Revises: 0007_gift_payments
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_device_name"
down_revision = "0007_gift_payments"
branch_labels = None
depends_on = None

# Ярлыки для переноса старых строк. Совпадают с тем, что показывают
# кабинет и мини-приложение, чтобы список не изменился на вид.
TYPE_LABELS = {
    "ios": "iPhone / iPad",
    "android": "Android",
    "macos": "macOS",
    "windows": "Windows",
    "linux": "Linux",
    "appletv": "Apple TV",
    "androidtv": "Смарт-ТВ",
}


def upgrade() -> None:
    op.add_column("devices", sa.Column("device_type", sa.String(32), nullable=True))

    known = ", ".join(f"'{t}'" for t in sorted(TYPE_LABELS))

    # 1. Тип = то, что лежало в name, но только если это действительно ключ
    #    типа. Произвольное legacy-имя длиннее 32 символов иначе не влезет
    #    в новую колонку и уронит миграцию.
    op.execute(f"UPDATE devices SET device_type = name WHERE name IN ({known})")

    # 2. Имя = человеческий ярлык этого типа.
    for type_key, label in TYPE_LABELS.items():
        op.execute(
            sa.text("UPDATE devices SET name = :label WHERE device_type = :type_key").bindparams(
                label=label, type_key=type_key
            )
        )

    # 3. Legacy-строки, где в name лежал не ключ типа, а произвольное имя
    #    (такие есть — модель всегда обещала "iPhone 15"). Имя у них уже
    #    правильное и остаётся как есть, а тип не угадать: ставим "ios",
    #    иначе в device_type попадёт имя целиком и не влезет в VARCHAR(32).
    op.execute("UPDATE devices SET device_type = 'ios' WHERE device_type IS NULL")

    op.alter_column("devices", "device_type", nullable=False)


def downgrade() -> None:
    # Возвращаем тип обратно в name — как было до разделения.
    op.execute("UPDATE devices SET name = device_type")
    op.drop_column("devices", "device_type")
