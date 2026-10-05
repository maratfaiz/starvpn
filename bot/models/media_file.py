"""
Загруженные из админки картинки (статьи Wiki, сообщения бота, иконка баннера).

Хранятся прямо в БД, а не на диске: контейнер бота пересобирается при
каждом деплое, и файлы в нём потерялись бы; бэкап базы сохраняет и
картинки. Размер ограничен (MAX_BYTES в bot/utils/media.py) — это
иллюстрации, а не файлохранилище. Отдаются по GET /media/{id}.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # file_id после первой отправки в Telegram — дальше бот шлёт картинку
    # по нему, не выгружая байты каждый раз.
    tg_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
