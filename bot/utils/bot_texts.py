"""
Редактируемые тексты бота и свои блоки (/admin → Бот).

Как это устроено:
- TEXTS — реестр всех редактируемых текстов системных экранов: ключ →
  текст по умолчанию (ровно то, что бот говорил до появления редактора),
  список подстановок ({days_left} и т.п.) и вид (сообщение или кнопка).
- SCREENS — схема экранов для админки: какие тексты у экрана и куда ведёт
  каждая кнопка. По ней рисуются блоки со стрелками. Экраны с kind="code"
  (устройства, подарок, оплата картой/криптой) — логика в коде, их тексты
  здесь не редактируются.
- Переопределения (BotText) и свои блоки (BotBlock) держатся в памяти
  процесса: бот и API работают в одном процессе (bot/main.py), поэтому
  сохранение в админке сразу видно боту — без рестарта.

В хендлерах: t("sub.text", days_left=…) вместо строкового литерала,
MenuText("btn.support") вместо F.text == "🎧 Поддержка".
"""

import json
import logging
import re
from html.parser import HTMLParser

from aiogram.filters import Filter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.bot_content import BotBlock, BotText

logger = logging.getLogger(__name__)

MSG = "message"
BTN = "button"

# key → (вид, текст по умолчанию, подстановки, подсказка для админки)
TEXTS: dict[str, tuple[str, str, tuple[str, ...], str]] = {
    # ── /start ──────────────────────────────────────────────────────────────
    "start.welcome_new": (MSG, (
        "⭐ <b>Добро пожаловать в STAR VPN</b>\n\n"
        "Твой личный инструмент для безопасного и свободного доступа в интернет. "
        "Мы используем протоколы нового поколения, которые обеспечивают стабильную связь и полную анонимность.\n\n"
        "С помощью этого бота ты можешь:\n"
        "• Мгновенно подключить свои устройства\n"
        "• Управлять подпиской и устройствами\n"
        "• Дарить подписку друзьям\n\n"
        "Нажми на кнопку ниже, чтобы открыть личный кабинет и активировать защиту."
    ), (), "Приветствие для тех, у кого нет активной подписки"),
    "start.trial_hint": (MSG, (
        "🎁 Тебе доступен <b>бесплатный период на 2 дня</b> — активируй прямо сейчас!"
    ), (), "Добавляется в конец приветствия, если пробный период ещё не использован"),
    "start.welcome_back": (MSG, (
        "⭐ <b>С возвращением в STAR VPN!</b>\n\n"
        "✅ Подписка активна — осталось <b>{days_left} дн.</b>\n\n"
        "Всё работает. Открой приложение, чтобы управлять устройствами."
    ), ("days_left",), "Приветствие для тех, у кого подписка активна"),
    "start.inline_prompt": (MSG, "👇", (), "Второе сообщение — над кнопками приложения/пробного периода"),
    "btn.open_app": (BTN, "🚀 Открыть приложение", (), "Открывает Mini App"),
    "btn.try_trial": (BTN, "🎁 Попробовать бесплатно — 2 дня", (), "Сразу активирует пробный период"),
    "btn.connect_inline": (BTN, "⚡️ Подключить VPN", (), "Показывает тарифы"),
    # ── Главное меню ───────────────────────────────────────────────────────
    "menu.title": (MSG, "🏠 Главное меню", (), "Сообщение при возврате в главное меню"),
    "btn.my_sub": (BTN, "📱 Моя подписка", (), "Видна, когда подписка активна"),
    "btn.connect": (BTN, "⚡️ Подключить VPN", (), "Видна, когда подписки нет"),
    "btn.trial": (BTN, "🎁 Пробный период", (), "Видна, пока пробный период не использован"),
    "btn.gift": (BTN, "🎁 Подарить VPN", (), "Видна, когда подписка активна"),
    "btn.referral": (BTN, "👥 Партнёрка", (), ""),
    "btn.support": (BTN, "🎧 Поддержка", (), ""),
    # ── Моя подписка ───────────────────────────────────────────────────────
    "sub.text": (MSG, (
        "📱 <b>Моя подписка</b>\n\n"
        "{status_icon} Осталось дней: <b>{days_left}</b>\n"
        "⏳ Действует до: <b>{expires}</b>"
    ), ("status_icon", "days_left", "expires"), ""),
    "btn.devices": (BTN, "📱 Устройства", (), ""),
    "btn.renew": (BTN, "🔄 Продлить подписку", (), ""),
    # ── Способ оплаты ──────────────────────────────────────────────────────
    "pay.choose": (MSG, "💳 <b>Выбери способ оплаты</b>", (), ""),
    "pay.unavailable": (MSG, (
        "💳 <b>Оплата временно недоступна</b>\n\n"
        "Все способы сейчас отключены — попробуй чуть позже или напиши в поддержку."
    ), (), "Если в Настройках выключены все способы оплаты"),
    "btn.pay_stars": (BTN, "⭐  Telegram Stars", (), ""),
    "btn.pay_card": (BTN, "💳  Банковская карта  (₽)", (), ""),
    "btn.pay_crypto": (BTN, "💎  Криптовалюта", (), ""),
    "btn.back": (BTN, "◀️ Назад", (), "Общая кнопка «назад» на экранах оплаты"),
    "stars.text": (MSG, (
        "⭐ <b>Оплата Telegram Stars</b>\n\n"
        "Дни добавляются к текущей подписке.\n"
        "Оплата мгновенная — прямо внутри Telegram."
    ), (), ""),
    # ── Тарифы ─────────────────────────────────────────────────────────────
    "plans.text": (MSG, (
        "⚡️ <b>Выберите тарифный план</b>\n\n"
        "Чем больше срок — тем выгоднее цена за месяц.\n"
        "Оплата в Telegram Stars ⭐ — мгновенно, без банков."
    ), (), "Кнопки тарифов строятся автоматически из цен"),
    "btn.gift_friend": (BTN, "🎁 Подарить подписку другу", (), ""),
    "paid.text": (MSG, (
        "🎉 <b>Спасибо за покупку!</b>\n\n"
        "📦 Тариф: <b>{plan}</b>\n"
        "⏳ Подписка действует до: <b>{expires}</b>\n\n"
        "Теперь перейди в <b>📱 Моя подписка → Устройства → ➕ Добавить устройство</b> "
        "и выбери тип своего устройства, чтобы получить ключ."
    ), ("plan", "expires"), "После успешной оплаты звёздами"),
    # ── Пробный период ─────────────────────────────────────────────────────
    "trial.offer": (MSG, (
        "🎁 <b>Тестовый доступ</b>\n\n"
        "Мы дарим тебе <b>2 дня полного безлимита</b>, "
        "чтобы ты проверил скорость лично."
    ), (), ""),
    "btn.activate_trial": (BTN, "🚀 Активировать тест", (), ""),
    "trial.used": (MSG, (
        "⚠️ <b>Тест уже был активирован</b>\n\n"
        "Пробный период можно использовать только один раз.\n"
        "Нажми <b>⚡️ Подключить VPN</b>, чтобы оформить подписку."
    ), (), "Если пробный период уже использован"),
    "trial.creating": (MSG, "⏳ Создаю твой VPN-аккаунт...", (), ""),
    "trial.activated": (MSG, (
        "✅ <b>Пробный период на {days} дня активирован!</b>\n\n"
        "Теперь перейди в <b>📱 Моя подписка → Устройства → ➕ Добавить устройство</b> "
        "и выбери тип своего устройства, чтобы получить ключ."
    ), ("days",), ""),
    # ── Партнёрка ──────────────────────────────────────────────────────────
    "referral.text": (MSG, (
        "👥 <b>Партнёрская программа STAR VPN</b>\n\n"
        "<b>Как работает:</b>\n"
        "Делись ссылкой → друг покупает подписку → "
        "за каждые <b>{milestone_size} оплативших друзей</b> тебе автоматически "
        "добавляется <b>+{bonus_days} дней</b> к твоей подписке. "
        "Никакого вывода — бонус применяется сразу.\n\n"
        "📈 <b>Твоя статистика:</b>\n"
        "👤 Приглашено: <b>{invited}</b> чел.\n"
        "✅ Оплатили подписку: <b>{paying}</b> чел.\n"
        "🎁 Всего получено дней: <b>{days_earned}</b>\n\n"
        "{next_milestone}\n\n"
        "🏆 <b>Достижения:</b>\n"
        "{achievements}\n\n"
        "🔗 <b>Твоя реферальная ссылка:</b>\n"
        "<code>{ref_link}</code>"
    ), ("milestone_size", "bonus_days", "invited", "paying", "days_earned",
        "next_milestone", "achievements", "ref_link"), ""),
    "btn.share": (BTN, "📤 Поделиться ссылкой", (), ""),
    "referral.share_text": (MSG, "Попробуй STAR VPN — быстрый и невидимый VPN! 🛡", (),
                            "Текст, который подставляется при пересылке ссылки другу (без разметки)"),
    # ── Поддержка ──────────────────────────────────────────────────────────
    "support.text": (MSG, (
        "🎧 <b>Служба поддержки</b>\n\n"
        "Возникли вопросы? Не работает подключение?\n"
        "Напиши нашему администратору — решим любую проблему.\n\n"
        "👉 <a href=\"{support_link}\">Написать в поддержку</a>"
    ), ("support_link",), "{support_link} — ссылка на SUPPORT_USERNAME из .env"),
    # ── Инструкции ─────────────────────────────────────────────────────────
    "instr.menu": (MSG, (
        "📚 <b>База знаний</b>\n\n"
        "Выбери своё устройство, чтобы получить пошаговую инструкцию по настройке:"
    ), (), ""),
    "btn.instructions": (BTN, "📚 Инструкции", (), "Под сообщением с ключом"),
    "btn.instr_back": (BTN, "◀️ К выбору устройства", (), ""),
    "instr.ios": (MSG, (
        "🍏 <b>Инструкция для iPhone / iPad</b>\n\n"
        "1. Скачай приложение <b>Streisand</b> из App Store:\n"
        "   → <a href=\"https://apps.apple.com/app/id6446544843\">Streisand в App Store</a>\n\n"
        "2. Открой <b>Streisand</b>, нажми «+» в верхнем углу\n\n"
        "3. Выбери «Import from Clipboard» или «Сканировать QR-код»\n\n"
        "4. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "5. Нажми «Connect» — готово! 🎉\n\n"
        "✅ Разрешение на VPN-профиль нужно подтвердить один раз."
    ), (), "iPhone / iPad"),
    "instr.android": (MSG, (
        "🤖 <b>Инструкция для Android</b>\n\n"
        "1. Скачай <b>v2rayNG</b> из Google Play:\n"
        "   → <a href=\"https://play.google.com/store/apps/details?id=com.v2ray.ang\">v2rayNG в Google Play</a>\n\n"
        "2. Открой приложение, нажми «+» (справа внизу)\n\n"
        "3. Выбери «Import config from QRcode» или «Input config manually»\n\n"
        "4. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "5. Нажми значок ▶️ — готово! 🎉\n\n"
        "✅ Разрешение на VPN нужно подтвердить один раз."
    ), (), "Android"),
    "instr.windows": (MSG, (
        "💻 <b>Инструкция для Windows</b>\n\n"
        "1. Скачай <b>v2rayN</b>:\n"
        "   → <a href=\"https://github.com/2dust/v2rayN/releases\">Последний релиз на GitHub</a>\n"
        "   (скачивай файл `v2rayN-With-Core.zip`)\n\n"
        "2. Распакуй архив и запусти `v2rayN.exe`\n\n"
        "3. Нажми «Сервера» → «Добавить сервер VLESS»\n\n"
        "4. Нажми «Импортировать из буфера» и вставь свою VLESS-ссылку\n\n"
        "5. Щёлкни правой кнопкой на иконке в трее → «Системный прокси» → «Автоконфигурация» — готово! 🎉"
    ), (), "Windows"),
    "instr.macos": (MSG, (
        "🍎 <b>Инструкция для macOS</b>\n\n"
        "1. Скачай <b>V2Box</b> из Mac App Store:\n"
        "   → <a href=\"https://apps.apple.com/app/id6446814690\">V2Box в App Store</a>\n\n"
        "2. Открой V2Box, нажми «+» → «Import from Clipboard»\n\n"
        "3. Вставь свою VLESS-ссылку (из раздела 🔗 Моё подключение)\n\n"
        "4. Нажми «Connect» — готово! 🎉\n\n"
        "✅ Разрешение системного расширения нужно подтвердить в Системных настройках."
    ), (), "macOS"),
    "instr.linux": (MSG, (
        "🐧 <b>Инструкция для Linux</b>\n\n"
        "1. Скачай <b>NekoRay</b> (AppImage):\n"
        "   → <a href=\"https://github.com/MatsuriDayo/nekoray/releases\">Последний релиз на GitHub</a>\n\n"
        "2. Сделай файл исполняемым: `chmod +x NekoRay*.AppImage` и запусти\n\n"
        "3. Меню «Program» → «Add profile from clipboard», предварительно скопировав свою VLESS-ссылку\n\n"
        "4. Выбери профиль двойным кликом, включи «System Proxy» или «TUN Mode» — готово! 🎉"
    ), (), "Linux"),
    "instr.appletv": (MSG, (
        "🍏 <b>Инструкция для Apple TV</b>\n\n"
        "1. На самом Apple TV: App Store → скачай <b>Happ</b>\n\n"
        "2. На телефоне возьми ссылку-подписку из раздела 🔗 Моё подключение — она проще, чем длинный ключ\n\n"
        "3. В Happ на Apple TV: «Добавить сервер» → «Добавить подписку» → введи ссылку с пульта\n\n"
        "4. Выбери сервер «STAR VPN» и подключись — готово! 🎉"
    ), (), "Apple TV"),
    "instr.androidtv": (MSG, (
        "📺 <b>Инструкция для Смарт-ТВ (Android TV)</b>\n\n"
        "1. На самом телевизоре: Google Play (или магазин приложений ТВ) → скачай <b>Happ</b>\n"
        "   Нет Google Play? APK можно взять на <a href=\"https://github.com/Happ-proxy/happ-android/releases\">GitHub</a>\n\n"
        "2. На телефоне возьми ссылку-подписку из раздела 🔗 Моё подключение — её проще ввести с пульта\n\n"
        "3. В Happ на ТВ: «Добавить сервер» → «Добавить подписку» → введи ссылку\n\n"
        "4. Выбери сервер «STAR VPN» и подключись — готово! 🎉"
    ), (), "Смарт-ТВ"),
}

# Экраны, над текстом которых можно поставить картинку (/admin → Бот).
# Хранится в BotText с ключом "image:<ключ текста>".
IMAGE_KEYS = {
    "start.welcome_new", "start.welcome_back", "menu.title", "sub.text", "pay.choose",
    "stars.text", "plans.text", "paid.text", "trial.offer", "trial.activated",
    "referral.text", "support.text", "instr.menu",
}

# Кнопки главного меню, которые можно скрыть (остальные — основа бота).
HIDEABLE = {"btn.gift", "btn.referral", "btn.support"}
# Кнопки нижней клавиатуры — их подписи должны быть уникальны: по ним бот
# узнаёт, какую кнопку нажали.
REPLY_BUTTONS = ("btn.my_sub", "btn.connect", "btn.trial", "btn.gift", "btn.referral", "btn.support")

# Экраны, на которые может вести кнопка своего блока → callback_data
# существующих хендлеров (или scr:* из bot/handlers/custom_blocks.py).
SCREEN_TARGETS: dict[str, tuple[str, str]] = {
    "main_menu": ("Главное меню", "back:main"),
    "subscription": ("Моя подписка", "sub:back"),
    "plans": ("Тарифы", "show_plans"),
    "pay_choice": ("Способ оплаты", "sub:pay_choice"),
    "trial": ("Активировать пробный период", "activate_trial"),
    "devices": ("Устройства", "sub:devices"),
    "instructions": ("Инструкции", "instr:pick"),
    "referral": ("Партнёрка", "scr:referral"),
    "support": ("Поддержка", "scr:support"),
    "gift": ("Подарить подписку", "gift:start"),
}

# Схема для админки. col/row — место блока на схеме. У кнопки to — id
# экрана, куда ведёт стрелка; back=True — возврат назад (без стрелки).
SCREENS: list[dict] = [
    {"id": "start", "title": "Приветствие (/start)", "col": 0, "row": 0,
     "texts": ["start.welcome_new", "start.trial_hint", "start.welcome_back", "start.inline_prompt"],
     "buttons": [{"key": "btn.open_app", "to": "mini_app"},
                 {"key": "btn.try_trial", "to": "trial"},
                 {"key": "btn.connect_inline", "to": "plans"},
                 {"label": "Нижняя клавиатура", "to": "main_menu"}]},
    {"id": "main_menu", "title": "Главное меню", "col": 1, "row": 0,
     "note": "Клавиатура внизу чата. Набор кнопок зависит от того, есть ли подписка.",
     "texts": ["menu.title"],
     "buttons": [{"key": "btn.my_sub", "to": "subscription"},
                 {"key": "btn.connect", "to": "plans"},
                 {"key": "btn.trial", "to": "trial"},
                 {"key": "btn.gift", "to": "gift"},
                 {"key": "btn.referral", "to": "referral"},
                 {"key": "btn.support", "to": "support"}]},
    {"id": "subscription", "title": "Моя подписка", "col": 2, "row": 0,
     "texts": ["sub.text"],
     "buttons": [{"key": "btn.devices", "to": "devices"},
                 {"key": "btn.renew", "to": "pay_choice"}]},
    {"id": "plans", "title": "Тарифы", "col": 2, "row": 1,
     "note": "Если оплата звёздами выключена — сразу экран «Способ оплаты».",
     "texts": ["plans.text", "paid.text"],
     "buttons": [{"label": "Кнопки тарифов (из цен)", "to": "invoice"},
                 {"key": "btn.gift_friend", "to": "gift"}]},
    {"id": "trial", "title": "Пробный период", "col": 2, "row": 2,
     "texts": ["trial.offer", "trial.used", "trial.creating", "trial.activated"],
     "buttons": [{"key": "btn.activate_trial", "to": "main_menu", "back": True}]},
    {"id": "referral", "title": "Партнёрка", "col": 2, "row": 3,
     "texts": ["referral.text", "referral.share_text"],
     "buttons": [{"key": "btn.share", "to": "share"}]},
    {"id": "support", "title": "Поддержка", "col": 2, "row": 4,
     "texts": ["support.text"], "buttons": []},
    {"id": "gift", "title": "Подарок другу", "col": 2, "row": 5, "kind": "code",
     "note": "Пошаговый сценарий (тариф → получатель → оплата) — логика в коде.", "buttons": []},
    {"id": "pay_choice", "title": "Способ оплаты", "col": 3, "row": 0,
     "texts": ["pay.choose", "pay.unavailable"],
     "buttons": [{"key": "btn.pay_stars", "to": "stars"},
                 {"key": "btn.pay_card", "to": "card"},
                 {"key": "btn.pay_crypto", "to": "crypto"},
                 {"key": "btn.back", "to": "subscription", "back": True}]},
    {"id": "devices", "title": "Устройства", "col": 3, "row": 1, "kind": "code",
     "note": "Добавление устройств и выдача ключей — логика в коде.",
     "buttons": [{"key": "btn.instructions", "to": "instructions"}]},
    {"id": "invoice", "title": "Счёт в Stars", "col": 3, "row": 2, "kind": "code",
     "note": "Счёт Telegram; после оплаты — текст «После оплаты» из блока «Тарифы».", "buttons": []},
    {"id": "stars", "title": "Оплата Stars", "col": 4, "row": 0,
     "texts": ["stars.text"],
     "buttons": [{"label": "Кнопки тарифов (из цен)", "to": "invoice"},
                 {"key": "btn.back", "to": "pay_choice", "back": True}]},
    {"id": "card", "title": "Оплата картой", "col": 4, "row": 1, "kind": "code",
     "note": "Robokassa — логика в коде.", "buttons": []},
    {"id": "crypto", "title": "Оплата криптой", "col": 4, "row": 2, "kind": "code",
     "note": "@CryptoBot — логика в коде.", "buttons": []},
    {"id": "instructions", "title": "Инструкции", "col": 4, "row": 3,
     "texts": ["instr.menu", "instr.ios", "instr.android", "instr.macos", "instr.windows",
               "instr.linux", "instr.appletv", "instr.androidtv"],
     "buttons": [{"label": "Кнопки устройств → инструкция", "to": "instructions", "back": True},
                 {"key": "btn.instr_back", "to": "instructions", "back": True}]},
]

RESERVED_COMMANDS = {
    "start", "admin", "user", "ban", "unban", "grant", "gadgets", "payments",
    "stats", "status", "broadcast", "message",
}

# ── Кеш ───────────────────────────────────────────────────────────────────────

_overrides: dict[str, str] = {}
_blocks: dict[int, dict] = {}


def _block_dict(b: BotBlock) -> dict:
    try:
        buttons = json.loads(b.buttons or "[]")
    except ValueError:
        buttons = []
    return {
        "id": b.id, "title": b.title, "text": b.text, "buttons": buttons, "image": b.image or "",
        "show_in_menu": bool(b.show_in_menu), "menu_label": b.menu_label,
        "command": b.command, "sort_order": b.sort_order,
    }


async def load_cache(session: AsyncSession) -> None:
    global _overrides, _blocks
    rows = (await session.execute(select(BotText))).scalars().all()
    _overrides = {r.key: r.value for r in rows}
    blocks = (await session.execute(select(BotBlock).order_by(BotBlock.sort_order, BotBlock.id))).scalars().all()
    _blocks = {b.id: _block_dict(b) for b in blocks}


def overrides() -> dict[str, str]:
    return dict(_overrides)


def custom_blocks() -> list[dict]:
    return sorted(_blocks.values(), key=lambda b: (b["sort_order"], b["id"]))


def get_block(block_id: int) -> dict | None:
    return _blocks.get(block_id)


# ── Использование в хендлерах ─────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def default(key: str) -> str:
    return TEXTS[key][1]


def t(key: str, **values: object) -> str:
    """Текст по ключу (правка из админки или по умолчанию) с подстановками.
    Неизвестные {слова} остаются как есть — правка текста не может уронить бота."""
    text = _overrides.get(key) or TEXTS[key][1]
    if not values:
        return text
    return _PLACEHOLDER_RE.sub(
        lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text
    )


def image_for(key: str) -> str:
    """Картинка над экраном: "media:<id>", https://… или ""."""
    return _overrides.get(f"image:{key}", "") if key in IMAGE_KEYS else ""


_IMAGE_URL_RE = re.compile(r"https?://\S{3,480}")


def validate_image_ref(ref: str) -> str | None:
    if not ref or ref.startswith("media:") and ref[6:].isdigit():
        return None
    if _IMAGE_URL_RE.fullmatch(ref):
        return None
    return "Картинка: загрузите файл или вставьте ссылку https://…"


def is_hidden(key: str) -> bool:
    return _overrides.get(f"hidden:{key}") == "1"


def button_variants(key: str) -> set[str]:
    """Текущая подпись + исходная: у пользователей может остаться старая
    клавиатура, отправленная до переименования, — она должна работать."""
    return {t(key), default(key)}


class MenuText(Filter):
    """Фильтр для кнопок нижней клавиатуры: MenuText("btn.support", "legacy текст")."""

    def __init__(self, key: str, *aliases: str) -> None:
        self.key = key
        self.aliases = set(aliases)

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        return message.text in button_variants(self.key) or message.text in self.aliases


# ── Свои блоки → клавиатура ───────────────────────────────────────────────────

def block_keyboard(block: dict) -> InlineKeyboardMarkup | None:
    rows = []
    for btn in block["buttons"]:
        label = btn.get("label") or "…"
        kind, target = btn.get("type"), str(btn.get("target") or "")
        if kind == "url":
            rows.append([InlineKeyboardButton(text=label, url=target)])
        elif kind == "block":
            rows.append([InlineKeyboardButton(text=label, callback_data=f"cb:{target}")])
        elif kind == "screen" and target in SCREEN_TARGETS:
            rows.append([InlineKeyboardButton(text=label, callback_data=SCREEN_TARGETS[target][1])])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def menu_blocks() -> list[dict]:
    return [b for b in custom_blocks() if b["show_in_menu"] and b["menu_label"]]


def block_by_menu_label(text: str) -> dict | None:
    return next((b for b in menu_blocks() if b["menu_label"] == text), None)


def block_by_command(command: str) -> dict | None:
    command = command.lower()
    return next((b for b in custom_blocks() if b["command"] and b["command"] == command), None)


# ── Проверка перед сохранением ────────────────────────────────────────────────

_TG_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "a", "code",
            "pre", "blockquote", "tg-spoiler", "span"}
_BAD_AMP_RE = re.compile(r"&(?!(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);)")
_BAD_LT_RE = re.compile(r"<(?![a-zA-Z/])")


class _TagChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.error: str | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if self.error:
            return
        if tag not in _TG_TAGS:
            self.error = f"Тег <{tag}> Telegram не поддерживает. Можно: <b>, <i>, <u>, <s>, <a>, <code>, <pre>, <blockquote>"
            return
        if tag == "a" and not dict(attrs).get("href"):
            self.error = "У ссылки <a> нет href"
            return
        self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.error:
            return
        if not self.stack or self.stack[-1] != tag:
            self.error = f"Тег </{tag}> закрыт не по порядку или лишний"
            return
        self.stack.pop()


def validate_html(text: str) -> str | None:
    """None — текст можно отправлять с parse_mode=HTML; иначе — причина."""
    if len(text) > 4000:
        return "Сообщение длиннее 4000 символов"
    if _BAD_LT_RE.search(text):
        return "Символ «<» вне тега — замените его на &lt;"
    if _BAD_AMP_RE.search(text):
        return "Символ «&» вне HTML-сущности — замените его на &amp;"
    checker = _TagChecker()
    checker.feed(text)
    checker.close()
    if checker.error:
        return checker.error
    if checker.stack:
        return f"Не закрыт тег <{checker.stack[-1]}>"
    return None


def validate_text(key: str, value: str) -> str | None:
    kind, _, placeholders, _ = TEXTS[key]
    if not value.strip():
        return "Текст не может быть пустым — нажмите «Сбросить», чтобы вернуть стандартный"
    if kind == BTN:
        if len(value) > 64:
            return "Подпись кнопки — не длиннее 64 символов"
        if "\n" in value:
            return "Подпись кнопки — в одну строку"
        return None
    unknown = [p for p in _PLACEHOLDER_RE.findall(value) if p not in placeholders]
    if unknown:
        allowed = ", ".join(f"{{{p}}}" for p in placeholders) or "нет"
        return f"Неизвестная подстановка {{{unknown[0]}}}. Доступные: {allowed}"
    if key == "referral.share_text":
        return None
    return validate_html(value)


def reply_labels(extra_overrides: dict[str, str | None] | None = None,
                 exclude_block: int | None = None) -> dict[str, str]:
    """Подпись → чья это кнопка, для проверки уникальности."""
    ov = dict(_overrides)
    for k, v in (extra_overrides or {}).items():
        if v is None:
            ov.pop(k, None)
        else:
            ov[k] = v
    labels = {ov.get(k) or default(k): f"кнопка «{default(k)}»" for k in REPLY_BUTTONS}
    for b in menu_blocks():
        if b["id"] != exclude_block:
            labels.setdefault(b["menu_label"], f"блок «{b['title']}»")
    return labels


async def save_texts(session: AsyncSession, values: dict[str, str | None],
                     hidden: dict[str, bool], images: dict[str, str] | None = None) -> None:
    for key, value in values.items():
        row = await session.get(BotText, key)
        if value is None or value == default(key):
            if row:
                await session.delete(row)
        elif row:
            row.value = value
        else:
            session.add(BotText(key=key, value=value))
    for key, ref in (images or {}).items():
        ikey = f"image:{key}"
        row = await session.get(BotText, ikey)
        if not ref and row:
            await session.delete(row)
        elif ref and row:
            row.value = ref
        elif ref:
            session.add(BotText(key=ikey, value=ref))
    for key, is_hide in hidden.items():
        hkey = f"hidden:{key}"
        row = await session.get(BotText, hkey)
        if is_hide and not row:
            session.add(BotText(key=hkey, value="1"))
        elif not is_hide and row:
            await session.delete(row)
    await session.commit()
    await load_cache(session)


async def reset_all(session: AsyncSession) -> None:
    await session.execute(delete(BotText))
    await session.commit()
    await load_cache(session)
