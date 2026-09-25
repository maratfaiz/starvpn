"""📚 Инструкции — device-specific setup guides."""

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.utils.bot_media import send_screen
from bot.utils.bot_texts import image_for, t

router = Router()

DEVICE_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🍏 iPhone / iPad", callback_data="instr:ios"),
        InlineKeyboardButton(text="🤖 Android", callback_data="instr:android"),
    ],
    [
        InlineKeyboardButton(text="🍎 macOS", callback_data="instr:macos"),
        InlineKeyboardButton(text="💻 Windows", callback_data="instr:windows"),
        InlineKeyboardButton(text="🐧 Linux", callback_data="instr:linux"),
    ],
    [
        InlineKeyboardButton(text="🍏 Apple TV", callback_data="instr:appletv"),
        InlineKeyboardButton(text="📺 Смарт-ТВ", callback_data="instr:androidtv"),
    ],
])

# Тексты инструкций редактируются в админке (/admin → Бот → Инструкции),
# по умолчанию — bot/utils/bot_texts.py (ключи instr.<устройство>).
GUIDES = ("ios", "android", "windows", "macos", "linux", "appletv", "androidtv")


@router.message(F.text == "📚 Инструкции")
async def instructions_menu(message: Message) -> None:
    await send_screen(message, t("instr.menu"), image=image_for("instr.menu"), reply_markup=DEVICE_MENU)


def _back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn.instr_back"), callback_data="instr:pick")],
    ])


@router.callback_query(F.data.startswith("instr:"))
async def show_guide(callback: CallbackQuery) -> None:
    device = callback.data.split(":", 1)[1]

    if device == "pick":
        await send_screen(
            callback.message, t("instr.menu"), image=image_for("instr.menu"), reply_markup=DEVICE_MENU,
        )
        await callback.answer()
        return

    if device not in GUIDES:
        await callback.answer("Инструкция не найдена.", show_alert=True)
        return

    await callback.message.answer(
        t(f"instr.{device}"),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=_back_to_menu_kb(),
    )
    await callback.answer()
