"""QR code generation helper using segno."""

import io
import segno
from aiogram.types import BufferedInputFile


def make_qr_photo(data: str, filename: str = "qr.png") -> BufferedInputFile:
    """Render a high-contrast QR code PNG and wrap it for aiogram sending."""
    qr = segno.make(data, error="l", micro=False)
    buf = io.BytesIO()
    qr.save(buf, kind="png", scale=12, border=2, dark="#ffffff", light="#0d1117")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename=filename)
