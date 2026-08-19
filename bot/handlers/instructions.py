"""📚 Инструкции — device-specific setup guides."""

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

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

GUIDES: dict[str, str] = {
    "ios": (
        "🍏 <b>Инструкция для iPhone / iPad</b>\n\n"
        "1. Скачай приложение <b>Streisand</b> из App Store:\n"
        "   → <a href=\"https://apps.apple.com/app/id6446544843\">Streisand в App Store</a>\n\n"
        "2. Открой <b>Streisand</b>, нажми «+» в верхнем углу\n\n"
        "3. Выбери «Import from Clipboard» или «Сканировать QR-код»\n\n"
        "4. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "5. Нажми «Connect» — готово! 🎉\n\n"
        "✅ Разрешение на VPN-профиль нужно подтвердить один раз."
    ),
    "android": (
        "🤖 <b>Инструкция для Android</b>\n\n"
        "1. Скачай <b>v2rayNG</b> из Google Play:\n"
        "   → <a href=\"https://play.google.com/store/apps/details?id=com.v2ray.ang\">v2rayNG в Google Play</a>\n\n"
        "2. Открой приложение, нажми «+» (справа внизу)\n\n"
        "3. Выбери «Import config from QRcode» или «Input config manually»\n\n"
        "4. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "5. Нажми значок ▶️ — готово! 🎉\n\n"
        "✅ Разрешение на VPN нужно подтвердить один раз."
    ),
    "windows": (
        "💻 <b>Инструкция для Windows</b>\n\n"
        "1. Скачай <b>v2rayN</b>:\n"
        "   → <a href=\"https://github.com/2dust/v2rayN/releases\">Последний релиз на GitHub</a>\n"
        "   (скачивай файл `v2rayN-With-Core.zip`)\n\n"
        "2. Распакуй архив и запусти `v2rayN.exe`\n\n"
        "3. Нажми «Сервера» → «Добавить сервер VLESS»\n\n"
        "4. Нажми «Импортировать из буфера» и вставь свою VLESS-ссылку\n\n"
        "5. Щёлкни правой кнопкой на иконке в трее → «Системный прокси» → «Автоконфигурация» — готово! 🎉"
    ),
    "macos": (
        "🍎 <b>Инструкция для macOS</b>\n\n"
        "1. Скачай <b>V2Box</b> из Mac App Store:\n"
        "   → <a href=\"https://apps.apple.com/app/id6446814690\">V2Box в App Store</a>\n\n"
        "2. Открой V2Box, нажми «+» → «Import from Clipboard»\n\n"
        "3. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "4. Нажми «Connect» — готово! 🎉\n\n"
        "✅ Разрешение системного расширения нужно подтвердить в Системных настройках."
    ),
    "linux": (
        "🐧 <b>Инструкция для Linux</b>\n\n"
        "1. Скачай <b>NekoRay</b> (AppImage):\n"
        "   → <a href=\"https://github.com/MatsuriDayo/nekoray/releases\">Последний релиз на GitHub</a>\n\n"
        "2. Сделай файл исполняемым: `chmod +x NekoRay*.AppImage` и запусти\n\n"
        "3. Меню «Program» → «Add profile from clipboard», предварительно скопировав свою VLESS-ссылку\n\n"
        "4. Выбери профиль двойным кликом, включи «System Proxy» или «TUN Mode» — готово! 🎉"
    ),
    "appletv": (
        "🍏 <b>Инструкция для Apple TV</b>\n\n"
        "1. На самом Apple TV: App Store → скачай <b>Happ</b>\n\n"
        "2. На телефоне возьми ссылку-подписку из раздела 🔗 Моё подключение — она проще, чем длинный ключ\n\n"
        "3. В Happ на Apple TV: «Добавить сервер» → «Добавить подписку» → введи ссылку с пульта\n\n"
        "4. Выбери сервер «STAR VPN» и подключись — готово! 🎉"
    ),
    "androidtv": (
        "📺 <b>Инструкция для Смарт-ТВ (Android TV)</b>\n\n"
        "1. На самом телевизоре: Google Play (или магазин приложений ТВ) → скачай <b>Happ</b>\n"
        "   Нет Google Play? APK можно взять на <a href=\"https://github.com/Happ-proxy/happ-android/releases\">GitHub</a>\n\n"
        "2. На телефоне возьми ссылку-подписку из раздела 🔗 Моё подключение — её проще ввести с пульта\n\n"
        "3. В Happ на ТВ: «Добавить сервер» → «Добавить подписку» → введи ссылку\n\n"
        "4. Выбери сервер «STAR VPN» и подключись — готово! 🎉"
    ),
}


@router.message(F.text == "📚 Инструкции")
async def instructions_menu(message: Message) -> None:
    await message.answer(
        "📚 <b>База знаний</b>\n\n"
        "Выберите ваше устройство, чтобы получить пошаговую инструкцию по настройке:",
        parse_mode="HTML",
        reply_markup=DEVICE_MENU,
    )


_BACK_TO_MENU_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️ К выбору устройства", callback_data="instr:pick")],
])


@router.callback_query(F.data.startswith("instr:"))
async def show_guide(callback: CallbackQuery) -> None:
    device = callback.data.split(":", 1)[1]

    if device == "pick":
        await callback.message.answer(
            "📚 <b>База знаний</b>\n\n"
            "Выбери своё устройство, чтобы получить пошаговую инструкцию по настройке:",
            parse_mode="HTML",
            reply_markup=DEVICE_MENU,
        )
        await callback.answer()
        return

    guide = GUIDES.get(device)
    if not guide:
        await callback.answer("Инструкция не найдена.", show_alert=True)
        return

    await callback.message.answer(
        guide,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=_BACK_TO_MENU_KB,
    )
    await callback.answer()
