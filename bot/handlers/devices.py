"""
📱 Управление устройствами пользователя.

Флоу:
  📱 Мои устройства → список устройств + кнопка Добавить
      ➕ Добавить → выбор типа (iOS / Android / macOS / Windows / Android TV / Apple TV)
      [Тип] → создание в Marzban → QR + ключ
      [Устройство] → карточка: статус / трафик / онлайн + [🔑 Ключ] [🗑 Удалить]

Marzban username: {type}_tg_{username_or_id}
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.device import Device, MAX_DEVICES
from bot.models.user import User
from bot.utils.marzban import marzban
from bot.utils.qr import make_qr_photo
from bot.utils.branding import set_vless_remark, subscription_url

router = Router()
logger = logging.getLogger(__name__)


# ─── типы устройств ──────────────────────────────────────────────────────────

DEVICE_TYPES: dict[str, dict] = {
    "ios":       {"label": "iPhone / iPad",  "icon": "🍎"},
    "android":   {"label": "Android",         "icon": "🤖"},
    "macos":     {"label": "macOS",            "icon": "💻"},
    "windows":   {"label": "Windows",          "icon": "🖥"},
    "androidtv": {"label": "Android TV",       "icon": "📺"},
    "appletv":   {"label": "Apple TV",         "icon": "🍏"},
}


def _type_icon(name: str) -> str:
    """Иконка по ключу типа или legacy-названию."""
    dt = DEVICE_TYPES.get(name)
    if dt:
        return dt["icon"]
    n = name.lower()
    if any(k in n for k in ("iphone", "ipad", "ios", "apple tv")):
        return "🍎"
    if any(k in n for k in ("android", "samsung", "xiaomi", "pixel")):
        return "🤖"
    if any(k in n for k in ("macbook", "mac", "imac")):
        return "💻"
    if any(k in n for k in ("windows", "пк", "pc", "ноутбук", "laptop")):
        return "🖥"
    if "tv" in n:
        return "📺"
    return "📱"


def _type_label(name: str) -> str:
    """Отображаемое название по ключу типа или legacy-названию."""
    dt = DEVICE_TYPES.get(name)
    return dt["label"] if dt else name


def _mz_username_for_type(
    type_key: str,
    telegram_id: int,
    username: str | None,
    existing: list[str],
) -> str:
    """Генерирует Marzban username: {type}_tg_{ident}[2..9]."""
    ident = username.lower() if username else str(telegram_id)
    base = f"{type_key}_tg_{ident}"
    if base not in existing:
        return base
    for i in range(2, 10):
        candidate = f"{type_key}{i}_tg_{ident}"
        if candidate not in existing:
            return candidate
    return f"{type_key}_tg_{telegram_id}"


async def _get_devices(telegram_id: int, session: AsyncSession) -> list[Device]:
    result = await session.execute(
        select(Device)
        .where(Device.telegram_id == telegram_id, Device.is_active.is_(True))
        .order_by(Device.slot)
    )
    return list(result.scalars().all())


def _fmt_online(online_at: int | None, now_ts: int) -> str:
    if not online_at:
        return "никогда не подключалось"
    diff = now_ts - online_at
    if diff < 60:
        return "🟢 онлайн прямо сейчас"
    if diff < 300:
        return f"🟡 {diff // 60} мин. назад"
    if diff < 3600:
        return f"🕐 {diff // 60} мин. назад"
    if diff < 86400:
        return f"🕐 {diff // 3600} ч. назад"
    return f"🕐 {diff // 86400} дн. назад"


# ─── клавиатуры ─────────────────────────────────────────────────────────────

def _list_kb(devices: list[Device], has_sub: bool) -> InlineKeyboardMarkup:
    rows = []
    for dev in devices:
        icon = _type_icon(dev.name)
        label = _type_label(dev.name)
        rows.append([InlineKeyboardButton(
            text=f"{icon} {label}",
            callback_data=f"dev:info:{dev.id}",
        )])

    if has_sub and len(devices) < MAX_DEVICES:
        rows.append([InlineKeyboardButton(
            text="➕ Добавить устройство",
            callback_data="dev:add",
        )])
    elif not has_sub:
        rows.append([InlineKeyboardButton(
            text="➕ Добавить устройство",
            callback_data="dev:no_sub",
        )])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _type_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍎 iPhone / iPad", callback_data="dev:add_type:ios"),
            InlineKeyboardButton(text="🤖 Android",        callback_data="dev:add_type:android"),
        ],
        [
            InlineKeyboardButton(text="💻 macOS",           callback_data="dev:add_type:macos"),
            InlineKeyboardButton(text="🖥 Windows",         callback_data="dev:add_type:windows"),
        ],
        [
            InlineKeyboardButton(text="📺 Android TV",      callback_data="dev:add_type:androidtv"),
            InlineKeyboardButton(text="🍏 Apple TV",        callback_data="dev:add_type:appletv"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="dev:list")],
    ])


def _key_or_sublink_kb(dev_id: int) -> InlineKeyboardMarkup:
    """Минимальный вариант — только два способа получить доступ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔑 Ключ",  callback_data=f"dev:link:{dev_id}"),
            InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"dev:sublink:{dev_id}"),
        ],
    ])


def _device_card_kb(dev_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔑 Ключ",  callback_data=f"dev:link:{dev_id}"),
            InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"dev:sublink:{dev_id}"),
        ],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"dev:del:{dev_id}")],
        [InlineKeyboardButton(text="◀️ К устройствам", callback_data="dev:list")],
    ])


# ─── главный экран ───────────────────────────────────────────────────────────

async def show_devices_screen(
    target: Message | CallbackQuery,
    session: AsyncSession,
    edit: bool = False,
) -> None:
    is_cb = isinstance(target, CallbackQuery)
    msg = target.message if is_cb else target
    tg_id = target.from_user.id

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user: User | None = result.scalar_one_or_none()
    if not user:
        await msg.answer("Сначала отправь /start.")
        return

    devices = await _get_devices(tg_id, session)

    # Миграция: старый marzban_username → слот 1 с типом ios
    if not devices and user.marzban_username:
        dev = Device(
            telegram_id=tg_id,
            slot=1,
            name="ios",
            marzban_username=user.marzban_username,
        )
        session.add(dev)
        await session.commit()
        devices = [dev]

    now = datetime.utcnow()
    has_sub = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    if devices:
        lines = [
            f"{_type_icon(d.name)} {_type_label(d.name)}"
            for d in devices
        ]
        devices_text = "\n".join(lines)
    else:
        devices_text = "<i>Устройств пока нет</i>"

    sub_note = ""
    if not has_sub:
        sub_note = "\n\n⚠️ <i>Нет активной подписки — добавить устройство нельзя.</i>"

    text = (
        f"📱 <b>Мои устройства</b> ({len(devices)}/{MAX_DEVICES})\n\n"
        f"{devices_text}"
        f"{sub_note}\n\n"
        "<i>Нажми на устройство — увидишь ключ и статус подключения.</i>"
    )
    kb = _list_kb(devices, has_sub)

    try:
        if edit or is_cb:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await msg.answer(text, parse_mode="HTML", reply_markup=kb)


# ─── добавить → выбор типа ───────────────────────────────────────────────────

@router.callback_query(F.data == "dev:add")
async def dev_add_start(callback: CallbackQuery, session: AsyncSession) -> None:
    tg_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer()
        return

    now = datetime.utcnow()
    if not (user.subscription_expires_at and user.subscription_expires_at > now):
        await callback.answer("Нет активной подписки.", show_alert=True)
        return

    devices = await _get_devices(tg_id, session)
    if len(devices) >= MAX_DEVICES:
        await callback.answer(f"Максимум {MAX_DEVICES} устройства.", show_alert=True)
        return

    await callback.message.edit_text(
        "📱 <b>Выбери тип устройства</b>",
        parse_mode="HTML",
        reply_markup=_type_select_kb(),
    )
    await callback.answer()


# ─── создание по типу ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dev:add_type:"))
async def dev_add_type(callback: CallbackQuery, session: AsyncSession) -> None:
    type_key = callback.data.split(":", 2)[2]
    if type_key not in DEVICE_TYPES:
        await callback.answer("Неизвестный тип.", show_alert=True)
        return

    tg_id = callback.from_user.id
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer()
        return

    now = datetime.utcnow()
    if not (user.subscription_expires_at and user.subscription_expires_at > now):
        await callback.answer("Нет активной подписки.", show_alert=True)
        return

    devices = await _get_devices(tg_id, session)
    if len(devices) >= MAX_DEVICES:
        await callback.answer(f"Максимум {MAX_DEVICES} устройства.", show_alert=True)
        return

    # Свободный слот (только для внутреннего порядка)
    occupied_slots = {d.slot for d in devices}
    slot = next((s for s in range(1, MAX_DEVICES + 1) if s not in occupied_slots), None)
    if not slot:
        await callback.answer("Нет свободных слотов.", show_alert=True)
        return

    existing_mz = [d.marzban_username for d in devices]
    mz_username = _mz_username_for_type(type_key, tg_id, user.username, existing_mz)
    dt = DEVICE_TYPES[type_key]
    days_left = max(1, (user.subscription_expires_at - now).days)

    await callback.message.edit_text(
        f"⏳ Создаю конфигурацию для <b>{dt['icon']} {dt['label']}</b>...",
        parse_mode="HTML",
    )
    await callback.answer()

    link: str | None = None
    try:
        mz = await marzban.create_user(
            telegram_id=tg_id,
            days=days_left,
            note=f"device|type:{type_key}|slot:{slot}|tg:{tg_id}",
            ip_limit=1,
            username=mz_username,
        )
        link = set_vless_remark(marzban.extract_vless_link(mz), type_key)
    except Exception as e:
        logger.warning("create_user failed (%s), trying get_or_create: %s", mz_username, e)
        try:
            mz = await marzban.get_or_create_user(mz_username, tg_id, days_left)
            link = set_vless_remark(marzban.extract_vless_link(mz), type_key)
        except Exception as e2:
            logger.error("get_or_create_user also failed for %s: %s", mz_username, e2)
            await callback.message.answer(
                "❌ Не удалось создать VPN-конфигурацию. Попробуй ещё раз или напиши в поддержку."
            )
            await show_devices_screen(callback, session)
            return

    dev = Device(
        telegram_id=tg_id,
        slot=slot,
        name=type_key,
        marzban_username=mz_username,
    )
    session.add(dev)
    await session.commit()

    if link:
        await callback.message.answer(
            f"✅ <b>{dt['icon']} {dt['label']}</b> добавлено!\n\n"
            "Получи ключ ниже — вручную (QR/ссылка для вставки в приложение) "
            "или подпиской (сама добавится в Happ, v2rayNG и т.п.):",
            parse_mode="HTML",
            reply_markup=_key_or_sublink_kb(dev.id),
        )
    else:
        await callback.message.answer(
            f"✅ <b>{dt['icon']} {dt['label']}</b> добавлено! "
            "Зайди в устройство, чтобы получить ключ.",
            parse_mode="HTML",
        )

    await show_devices_screen(callback, session)


# ─── карточка устройства ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dev:info:"))
async def dev_info(callback: CallbackQuery, session: AsyncSession) -> None:
    dev_id = int(callback.data.split(":")[2])
    result = await session.execute(select(Device).where(Device.id == dev_id))
    dev = result.scalar_one_or_none()

    if not dev or dev.telegram_id != callback.from_user.id:
        await callback.answer("Устройство не найдено.", show_alert=True)
        return

    await callback.answer("⏳")

    icon = _type_icon(dev.name)
    label = _type_label(dev.name)
    now_ts = int(datetime.utcnow().timestamp())
    added = dev.created_at.strftime("%d.%m.%Y") if dev.created_at else "—"

    traffic_str = "—"
    online_str = "нет данных"
    status_str = "—"
    mz_ok = False

    try:
        mz = await marzban.get_user(dev.marzban_username)
        used = mz.get("used_traffic", 0) or 0
        traffic_str = f"{used / 1_073_741_824:.2f} ГБ"
        status_map = {
            "active":   "🟢 Активен",
            "disabled": "🔴 Отключён",
            "expired":  "🟡 Истёк",
            "limited":  "🟠 Лимит трафика",
        }
        status_str = status_map.get(mz.get("status", ""), mz.get("status", "—"))
        online_str = _fmt_online(mz.get("online_at"), now_ts)
        mz_ok = True
    except Exception as e:
        logger.warning("Marzban get_user failed for %s: %s", dev.marzban_username, e)
        online_str = "⚠️ нет связи с сервером"
        status_str = "⚠️ нет связи"

    text = (
        f"{icon} <b>{label}</b>\n\n"
        f"🔌 Статус:           {status_str}\n"
        f"🕐 Последний онлайн: {online_str}\n"
        f"📡 Трафик:           <b>{traffic_str}</b>\n"
        f"📅 Добавлено:        {added}"
    )
    if not mz_ok:
        text += "\n\n<i>⚠️ Данные могут быть неактуальны — сервер недоступен.</i>"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=_device_card_kb(dev_id),
    )


# ─── ключ / QR ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dev:link:"))
async def dev_show_link(callback: CallbackQuery, session: AsyncSession) -> None:
    dev_id = int(callback.data.split(":")[2])
    result = await session.execute(select(Device).where(Device.id == dev_id))
    dev = result.scalar_one_or_none()

    if not dev or dev.telegram_id != callback.from_user.id:
        await callback.answer("Устройство не найдено.", show_alert=True)
        return

    await callback.answer("⏳")

    user_r = await session.execute(select(User).where(User.telegram_id == dev.telegram_id))
    owner = user_r.scalar_one_or_none()
    now = datetime.utcnow()
    exp = owner.subscription_expires_at if owner else None
    days_left = max(1, (exp - now).days) if exp and exp > now else 30

    try:
        mz = await marzban.get_or_create_user(dev.marzban_username, dev.telegram_id, days_left)
        link = set_vless_remark(marzban.extract_vless_link(mz), dev.name)
    except Exception as e:
        logger.error("dev:link failed for %s: %s", dev.marzban_username, e)
        await callback.message.answer(
            "❌ Не удалось получить ключ. Попробуй ещё раз или напиши в поддержку."
        )
        return

    if not link:
        await callback.message.answer("❌ Ссылка недоступна — обратись в поддержку.")
        return

    from bot.handlers.payment import _instructions_kb

    icon = _type_icon(dev.name)
    label = _type_label(dev.name)
    qr = make_qr_photo(link, f"dev_{dev.id}.png")
    await callback.message.answer_photo(
        qr,
        caption=(
            f"🔑 <b>Ваш ключ — {icon} {label}</b>\n\n"
            f"<code>{link}</code>\n\n"
            "👆 Нажми на ключ, чтобы скопировать, затем вставь в приложение"
        ),
        parse_mode="HTML",
        reply_markup=_instructions_kb(),
    )


@router.callback_query(F.data.startswith("dev:sublink:"))
async def dev_show_sublink(callback: CallbackQuery, session: AsyncSession) -> None:
    """Ссылка-подписка: откроется в браузере страницей STAR VPN, либо
    сама добавится в Happ/v2rayNG/... если открыть её оттуда."""
    dev_id = int(callback.data.split(":")[2])
    result = await session.execute(select(Device).where(Device.id == dev_id))
    dev = result.scalar_one_or_none()

    if not dev or dev.telegram_id != callback.from_user.id:
        await callback.answer("Устройство не найдено.", show_alert=True)
        return

    await callback.answer()
    icon = _type_icon(dev.name)
    label = _type_label(dev.name)
    await callback.message.answer(
        f"🔗 <b>Ссылка-подписка — {icon} {label}</b>\n\n"
        f"<code>{subscription_url(dev.marzban_username)}</code>\n\n"
        "Открой в Happ, v2rayNG или другом клиенте — сервер добавится "
        "автоматически под именем «STAR VPN». Либо открой прямо в браузере, "
        "если нужна пошаговая инструкция.",
        parse_mode="HTML",
    )


# ─── удаление ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("dev:del:"))
async def dev_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    dev_id = int(callback.data.split(":")[2])
    result = await session.execute(select(Device).where(Device.id == dev_id))
    dev = result.scalar_one_or_none()

    if not dev or dev.telegram_id != callback.from_user.id:
        await callback.answer("Устройство не найдено.", show_alert=True)
        return

    icon = _type_icon(dev.name)
    label = _type_label(dev.name)
    await callback.message.edit_text(
        f"🗑 Удалить <b>{icon} {label}</b>?\n\n"
        "VPN-доступ с этого устройства будет отключён.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"dev:delok:{dev_id}"),
            InlineKeyboardButton(text="❌ Отмена",      callback_data=f"dev:info:{dev_id}"),
        ]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dev:delok:"))
async def dev_delete_ok(callback: CallbackQuery, session: AsyncSession) -> None:
    dev_id = int(callback.data.split(":")[2])
    result = await session.execute(select(Device).where(Device.id == dev_id))
    dev = result.scalar_one_or_none()

    if not dev or dev.telegram_id != callback.from_user.id:
        await callback.answer("Устройство не найдено.", show_alert=True)
        return

    icon = _type_icon(dev.name)
    label = _type_label(dev.name)

    dev.is_active = False
    try:
        await marzban.disable_user(dev.marzban_username)
    except Exception as e:
        logger.warning("Cannot disable marzban user %s: %s", dev.marzban_username, e)

    await session.commit()
    await callback.answer("Удалено!")

    await callback.message.edit_text(
        f"✅ <b>{icon} {label}</b> удалено.\nVPN-доступ с этого устройства отключён.",
        parse_mode="HTML",
    )
    await show_devices_screen(callback, session)


# ─── вспомогательные колбэки ─────────────────────────────────────────────────

@router.callback_query(F.data == "dev:list")
async def dev_list(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await show_devices_screen(callback, session)


@router.callback_query(F.data == "dev:no_sub")
async def dev_no_sub(callback: CallbackQuery) -> None:
    await callback.answer("Оформи подписку, чтобы добавить устройство.", show_alert=True)


@router.callback_query(F.data == "dev:cancel")
async def dev_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.edit_text("❌ Добавление отменено.")
    except Exception:
        pass
    await callback.answer()
