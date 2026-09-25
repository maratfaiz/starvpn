"""Отправка экрана бота с картинкой сверху (/admin → Бот → «Картинка»).

Картинка — это "media:<id>" (загружена в админку, bot/models/media_file.py)
или https://-ссылка. Текст идёт подписью к фото; если он длиннее лимита
подписи Telegram (1024), фото уходит отдельным сообщением над текстом.
Без картинки всё работает как раньше — обычное текстовое сообщение.
"""

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, Message

from bot.models.media_file import MediaFile
from bot.utils.database import AsyncSessionLocal
from bot.utils.media import parse_media_ref

logger = logging.getLogger(__name__)

CAPTION_LIMIT = 1024

# media_id → file_id в Telegram: после первой отправки байты больше не грузим.
_file_ids: dict[int, str] = {}


async def _photo_for(ref: str) -> tuple[object | None, int | None]:
    media_id = parse_media_ref(ref)
    if media_id is None:
        return (ref if ref.startswith(("https://", "http://")) else None), None
    if media_id in _file_ids:
        return _file_ids[media_id], media_id
    async with AsyncSessionLocal() as session:
        media = await session.get(MediaFile, media_id)
    if not media:
        return None, None
    if media.tg_file_id:
        _file_ids[media_id] = media.tg_file_id
        return media.tg_file_id, media_id
    ext = media.content_type.split("/")[-1]
    return BufferedInputFile(media.data, filename=f"image.{ext}"), media_id


async def _remember_file_id(media_id: int, sent: Message) -> None:
    if media_id in _file_ids or not sent.photo:
        return
    file_id = sent.photo[-1].file_id
    _file_ids[media_id] = file_id
    async with AsyncSessionLocal() as session:
        media = await session.get(MediaFile, media_id)
        if media:
            media.tg_file_id = file_id
            await session.commit()


async def send_screen(
    message: Message,
    text: str,
    *,
    image: str = "",
    reply_markup=None,
    edit: bool = False,
    disable_web_page_preview: bool | None = None,
) -> None:
    """edit=True — заменить сообщение (навигация по inline-кнопкам)."""
    photo, media_id = await _photo_for(image) if image else (None, None)

    if photo is None:
        if edit and not message.photo:
            try:
                await message.edit_text(
                    text, parse_mode="HTML", reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview,
                )
                return
            except TelegramBadRequest:
                pass  # сообщение не изменилось или его уже нельзя править
        elif edit:
            await _delete_quietly(message)
        await message.answer(
            text, parse_mode="HTML", reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
        return

    if edit:
        await _delete_quietly(message)
    try:
        if len(text) <= CAPTION_LIMIT:
            sent = await message.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            sent = await message.answer_photo(photo)
            await message.answer(
                text, parse_mode="HTML", reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
    except TelegramBadRequest as e:
        # Битая ссылка на картинку не должна ломать экран — шлём просто текст.
        logger.warning("Bot image %s failed: %s", image, e)
        await message.answer(
            text, parse_mode="HTML", reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
        return
    if media_id is not None:
        await _remember_file_id(media_id, sent)


async def _delete_quietly(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
