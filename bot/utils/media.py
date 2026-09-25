"""Картинки, загруженные из админки (bot/models/media_file.py).

Тип определяется по первым байтам файла, а не по имени/заголовку от
браузера. SVG не принимается: в нём может быть <script>, а файлы
отдаются с нашего домена.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.media_file import MediaFile

MAX_BYTES = 5 * 1024 * 1024

_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def sniff_image_type(data: bytes) -> str | None:
    for sig, ctype in _SIGNATURES:
        if data.startswith(sig):
            return ctype
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def save_image(data: bytes, filename: str, uploaded_by: str | None, session: AsyncSession) -> MediaFile:
    """Проверяет и сохраняет картинку. ValueError — с текстом для админки."""
    if not data:
        raise ValueError("Пустой файл")
    if len(data) > MAX_BYTES:
        raise ValueError(f"Файл больше {MAX_BYTES // 1024 // 1024} МБ")
    ctype = sniff_image_type(data)
    if not ctype:
        raise ValueError("Поддерживаются картинки PNG, JPEG, GIF и WebP")
    media = MediaFile(
        filename=(filename or "")[:200], content_type=ctype, size=len(data),
        data=data, uploaded_by=uploaded_by,
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
    return media


def media_url(media_id: int) -> str:
    return f"/media/{media_id}"


def parse_media_ref(ref: str) -> int | None:
    """"media:12" → 12; иначе None."""
    if ref.startswith("media:") and ref[6:].isdigit():
        return int(ref[6:])
    return None
