"""
Свои блоки, созданные в админке (/admin → Бот): показ блока по кнопке
(cb:<id>), по кнопке главного меню и по команде (/команда). Плюс scr:* —
переходы из своих блоков на системные экраны, у которых раньше не было
inline-входа (партнёрка, поддержка).
"""

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils import bot_texts

router = Router()
logger = logging.getLogger(__name__)


async def _send_block(message: Message, block: dict, edit: bool = False) -> None:
    kwargs = {
        "parse_mode": "HTML",
        "reply_markup": bot_texts.block_keyboard(block),
        "disable_web_page_preview": True,
    }
    if edit:
        try:
            await message.edit_text(block["text"], **kwargs)
            return
        except TelegramBadRequest:
            # Сообщение с фото/ключом или без изменений — отправим новое.
            pass
    await message.answer(block["text"], **kwargs)


@router.callback_query(F.data.startswith("cb:"))
async def open_block(callback: CallbackQuery) -> None:
    raw = callback.data.split(":", 1)[1]
    block = bot_texts.get_block(int(raw)) if raw.isdigit() else None
    if not block:
        await callback.answer("Этот раздел больше недоступен.", show_alert=True)
        return
    await _send_block(callback.message, block, edit=True)
    await callback.answer()


@router.callback_query(F.data == "scr:referral")
async def open_referral(callback: CallbackQuery, session: AsyncSession) -> None:
    from bot.handlers.referral import send_referral_info
    await send_referral_info(callback.message, callback.from_user.id, session)
    await callback.answer()


@router.callback_query(F.data == "scr:support")
async def open_support(callback: CallbackQuery) -> None:
    from bot.handlers.start import support_text
    await callback.message.answer(support_text(), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


def _menu_block(message: Message) -> dict | bool:
    block = bot_texts.block_by_menu_label(message.text) if message.text else None
    return {"block": block} if block else False


def _command_block(message: Message) -> dict | bool:
    if not message.text or not message.text.startswith("/"):
        return False
    command = message.text[1:].split(maxsplit=1)[0].split("@", 1)[0] if len(message.text) > 1 else ""
    block = bot_texts.block_by_command(command) if command else None
    return {"block": block} if block else False


@router.message(_menu_block)
async def menu_block(message: Message, block: dict) -> None:
    await _send_block(message, block)


@router.message(_command_block)
async def command_block(message: Message, block: dict) -> None:
    await _send_block(message, block)
