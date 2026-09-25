"""
Панель администратора STAR VPN.
Доступ: только TELEGRAM_ADMIN_ID.
"""

import asyncio
import html
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.device import Device
from bot.models.payment import Payment
from bot.models.user import User
from bot.states.payment_states import AdminForm
from bot.utils.marzban import marzban
from bot.utils.vpn_access import set_vpn_enabled

router = Router()
logger = logging.getLogger(__name__)

_pending_broadcast: dict[int, str] = {}


# ─────────────────────────────── helpers ────────────────────────────────────

def _admin(tg_id: int) -> bool:
    return tg_id == settings.telegram_admin_id


async def _resolve(arg: str, session: AsyncSession) -> User | None:
    arg = arg.strip()
    if arg.lstrip("-").isdigit():
        r = await session.execute(select(User).where(User.telegram_id == int(arg)))
    else:
        r = await session.execute(select(User).where(func.lower(User.username) == arg.lstrip("@").lower()).limit(1))
    return r.scalar_one_or_none()


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else "—"


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])


async def _err(msg: Message, e: Exception) -> None:
    """Показать ошибку администратору."""
    await msg.answer(f"❌ Ошибка: <code>{e}</code>", parse_mode="HTML")


# ─────────────────────── /admin — главное меню ──────────────────────────────

def _admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Инфо о юзере",    callback_data="adm:userinfo"),
            InlineKeyboardButton(text="⭐ Выдать подписку",  callback_data="adm:grant"),
        ],
        [
            InlineKeyboardButton(text="🚫 Забанить",         callback_data="adm:ban"),
            InlineKeyboardButton(text="✅ Разбанить",         callback_data="adm:unban"),
        ],
        [
            InlineKeyboardButton(text="📱 Активность юзера", callback_data="adm:gadgets"),
            InlineKeyboardButton(text="📋 Последние платежи", callback_data="adm:payments"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка",         callback_data="adm:broadcast"),
            InlineKeyboardButton(text="✉️ Написать юзеру",   callback_data="adm:message"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика",       callback_data="adm:stats"),
            InlineKeyboardButton(text="🛰 Статус Marzban",   callback_data="adm:status"),
        ],
    ])


@router.message(Command("admin"))
async def admin_menu(message: Message, state: FSMContext) -> None:
    if not _admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        "🛠 <b>Панель администратора STAR VPN</b>\n\n"
        "👤 <b>Инфо о юзере</b> — досье из БД + Marzban\n"
        "⭐ <b>Выдать подписку</b> — создать/продлить доступ\n"
        "🚫 <b>Забанить</b> — заблокировать пользователя\n"
        "✅ <b>Разбанить</b> — список забаненных → выбор\n"
        "📱 <b>Активность юзера</b> — онлайн, трафик\n"
        "📋 <b>Последние платежи</b> — последние 10 оплат Stars\n"
        "📢 <b>Рассылка</b> — написать всем\n"
        "✉️ <b>Написать юзеру</b> — личное сообщение\n"
        "📊 <b>Статистика</b> — пользователи и Stars\n"
        "🛰 <b>Статус Marzban</b> — проверка сервера",
        parse_mode="HTML",
        reply_markup=_admin_kb(),
    )


# ─────────────────── кнопки → запуск FSM-диалога ────────────────────────────

@router.callback_query(F.data == "adm:userinfo")
async def btn_userinfo(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.userinfo_target)
    await cb.message.answer(
        "👤 Введи ID или @username пользователя:",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:grant")
async def btn_grant(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.grant_user)
    await cb.message.answer(
        "⭐ Кому выдать подписку? Введи ID или @username:",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:ban")
async def btn_ban(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.ban_target)
    await cb.message.answer(
        "🚫 Кого забанить? Введи ID или @username:",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:unban")
async def btn_unban(cb: CallbackQuery, session: AsyncSession) -> None:
    """Показывает список забаненных пользователей кнопками."""
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await cb.answer()

    try:
        result = await session.execute(
            select(User).where(User.is_banned.is_(True))
        )
        banned_users = result.scalars().all()
    except Exception as e:
        await cb.message.answer(f"❌ Ошибка БД: <code>{e}</code>", parse_mode="HTML")
        return

    if not banned_users:
        await cb.message.answer("✅ Забаненных пользователей нет.")
        return

    buttons = []
    for u in banned_users:
        label = f"@{u.username}" if u.username else str(u.telegram_id)
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"unban:{u.telegram_id}",
        )])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")])

    await cb.message.answer(
        f"✅ <b>Выбери кого разбанить</b> ({len(banned_users)} чел.):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("unban:"))
async def unban_click(cb: CallbackQuery, session: AsyncSession) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    tg_id = int(cb.data.split(":")[1])
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await cb.answer("Пользователь не найден.", show_alert=True); return
    await cb.message.edit_reply_markup(reply_markup=None)
    await _do_unban(cb.message, user, session)
    await cb.answer()


@router.callback_query(F.data == "adm:gadgets")
async def btn_gadgets(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.gadgets_target)
    await cb.message.answer(
        "📱 Чью активность показать? Введи ID или @username:",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:broadcast")
async def btn_broadcast(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.broadcast_text)
    await cb.message.answer(
        "📢 Введи текст рассылки (HTML поддерживается):",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:message")
async def btn_message(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.set_state(AdminForm.message_user)
    await cb.message.answer(
        "✉️ Кому написать? Введи ID или @username:",
        reply_markup=_cancel_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "adm:payments")
async def btn_payments(cb: CallbackQuery, session: AsyncSession) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await cb.answer("⏳ Загружаю...")
    await _do_payments(cb.message, session)


@router.callback_query(F.data == "adm:stats")
async def btn_stats(cb: CallbackQuery, session: AsyncSession) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await cb.answer("⏳ Загружаю...")
    await _do_stats(cb.message, session)


@router.callback_query(F.data == "adm:status")
async def btn_status(cb: CallbackQuery) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await cb.answer("⏳ Проверяю...")
    await _do_status(cb.message)


@router.callback_query(F.data == "admin_cancel")
async def cancel_action(cb: CallbackQuery, state: FSMContext) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    await state.clear()
    await cb.message.edit_text("❌ Действие отменено.")
    await cb.answer()


# ─────────────────────── FSM-обработчики ────────────────────────────────────

@router.message(AdminForm.userinfo_target)
async def fsm_userinfo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    await state.clear()
    try:
        user = await _resolve(message.text or "", session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{html.escape(message.text or '')}</b> не найден.", parse_mode="HTML")
            return
        await message.answer(await _user_card(user, session), parse_mode="HTML")
    except Exception as e:
        await _err(message, e)


@router.message(AdminForm.ban_target)
async def fsm_ban(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    await state.clear()
    try:
        user = await _resolve(message.text or "", session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{html.escape(message.text or '')}</b> не найден.", parse_mode="HTML")
            return
        await _do_ban(message, user, session)
    except Exception as e:
        await _err(message, e)


@router.message(AdminForm.grant_user)
async def fsm_grant_user(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    try:
        user = await _resolve(message.text or "", session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{html.escape(message.text or '')}</b> не найден.", parse_mode="HTML")
            await state.clear()
            return
        await state.update_data(grant_tg_id=user.telegram_id)
        await state.set_state(AdminForm.grant_days)
        await message.answer(
            f"✅ {html.escape(user.full_name or '')} (<code>{user.telegram_id}</code>)\n"
            "На сколько дней выдать подписку?",
            parse_mode="HTML",
            reply_markup=_cancel_kb(),
        )
    except Exception as e:
        await state.clear()
        await _err(message, e)


@router.message(AdminForm.grant_days)
async def fsm_grant_days(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❌ Введи целое число дней, например: <b>30</b>", parse_mode="HTML")
        return
    data = await state.get_data()
    await state.clear()
    try:
        result = await session.execute(select(User).where(User.telegram_id == data["grant_tg_id"]))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return
        await _do_grant(message, user, int(text), session)
    except Exception as e:
        await _err(message, e)


@router.message(AdminForm.gadgets_target)
async def fsm_gadgets(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    await state.clear()
    try:
        user = await _resolve(message.text or "", session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{html.escape(message.text or '')}</b> не найден.", parse_mode="HTML")
            return
        await _do_gadgets(message, user)
    except Exception as e:
        await _err(message, e)


@router.message(AdminForm.broadcast_text)
async def fsm_broadcast_text(message: Message, state: FSMContext) -> None:
    if not _admin(message.from_user.id):
        return
    _pending_broadcast[message.from_user.id] = message.text or ""
    await state.clear()
    await message.answer(
        f"📢 <b>Предпросмотр:</b>\n\n{message.text}\n\nОтправить всем?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Отмена",    callback_data="broadcast_cancel"),
            ]
        ]),
    )


@router.message(AdminForm.message_user)
async def fsm_msg_user(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    try:
        user = await _resolve(message.text or "", session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{html.escape(message.text or '')}</b> не найден.", parse_mode="HTML")
            await state.clear()
            return
        await state.update_data(msg_tg_id=user.telegram_id)
        await state.set_state(AdminForm.message_text)
        await message.answer(
            f"✅ {html.escape(user.full_name or '')} (<code>{user.telegram_id}</code>)\nВведи текст сообщения:",
            parse_mode="HTML",
            reply_markup=_cancel_kb(),
        )
    except Exception as e:
        await state.clear()
        await _err(message, e)


@router.message(AdminForm.message_text)
async def fsm_msg_text(message: Message, state: FSMContext) -> None:
    if not _admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    tg_id = data.get("msg_tg_id")
    try:
        await message.bot.send_message(tg_id, message.text or "", parse_mode="HTML")
        await message.answer(f"✅ Отправлено пользователю <code>{tg_id}</code>.", parse_mode="HTML")
    except Exception as e:
        await _err(message, e)


# ─────────────────── прямые команды (альтернатива кнопкам) ──────────────────

@router.message(Command("user"))
async def cmd_user(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /user &lt;id|@username&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer(f"❌ Пользователь <b>{parts[1]}</b> не найден.", parse_mode="HTML"); return
        await message.answer(await _user_card(user, session), parse_mode="HTML")
    except Exception as e:
        await _err(message, e)


@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /ban &lt;id|@username&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer("❌ Пользователь не найден."); return
        await _do_ban(message, user, session)
    except Exception as e:
        await _err(message, e)


@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /unban &lt;id|@username&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer("❌ Пользователь не найден."); return
        await _do_unban(message, user, session)
    except Exception as e:
        await _err(message, e)


@router.message(Command("grant"))
async def cmd_grant(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 3 or not parts[2].isdigit():
        await message.answer("Использование: /grant &lt;id|@u&gt; &lt;дней&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer("❌ Пользователь не найден."); return
        await _do_grant(message, user, int(parts[2]), session)
    except Exception as e:
        await _err(message, e)


@router.message(Command("gadgets"))
async def cmd_gadgets(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /gadgets &lt;id|@username&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer("❌ Пользователь не найден."); return
        await _do_gadgets(message, user)
    except Exception as e:
        await _err(message, e)


@router.message(Command("payments"))
async def cmd_payments(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    await _do_payments(message, session)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    await _do_stats(message, session)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not _admin(message.from_user.id):
        return
    await _do_status(message)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    if not _admin(message.from_user.id):
        return
    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer("Использование: /broadcast &lt;текст&gt;", parse_mode="HTML"); return
    _pending_broadcast[message.from_user.id] = text
    await message.answer(
        f"📢 <b>Предпросмотр:</b>\n\n{text}\n\nОтправить всем?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="❌ Отмена",    callback_data="broadcast_cancel"),
            ]
        ]),
    )


@router.message(Command("message"))
async def cmd_message(message: Message, session: AsyncSession) -> None:
    if not _admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /message &lt;id|@u&gt; &lt;текст&gt;", parse_mode="HTML"); return
    try:
        user = await _resolve(parts[1], session)
        if not user:
            await message.answer("❌ Пользователь не найден."); return
        await message.bot.send_message(user.telegram_id, parts[2], parse_mode="HTML")
        await message.answer(f"✅ Отправлено → <code>{user.telegram_id}</code>.", parse_mode="HTML")
    except Exception as e:
        await _err(message, e)


# ──────────────────── broadcast confirm/cancel ───────────────────────────────

@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(cb: CallbackQuery, session: AsyncSession) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    text = _pending_broadcast.pop(cb.from_user.id, None)
    if not text:
        await cb.answer("Нет текста.", show_alert=True); return
    await cb.message.edit_reply_markup(reply_markup=None)
    ids = list((await session.execute(select(User.telegram_id))).scalars().all())
    status_msg = await cb.message.answer(
        f"📢 Рассылка <b>{len(ids)}</b> пользователям...", parse_mode="HTML"
    )
    sent = failed = 0
    for uid in ids:
        try:
            await cb.bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status_msg.edit_text(
        f"✅ Готово. Отправлено: <b>{sent}</b>, ошибок: <b>{failed}</b>.", parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(cb: CallbackQuery) -> None:
    if not _admin(cb.from_user.id):
        await cb.answer(); return
    _pending_broadcast.pop(cb.from_user.id, None)
    await cb.message.edit_text("❌ Рассылка отменена.")
    await cb.answer()


# ─────────────────────── бизнес-логика ──────────────────────────────────────

async def _user_card(user: User, session: AsyncSession | None = None) -> str:
    now = datetime.utcnow()
    sep = "─" * 22

    # Подписка
    sub = user.subscription_expires_at
    if sub and sub > now:
        days_left = (sub - now).days
        hours_left = ((sub - now).seconds // 3600)
        sub_str = f"{sub.strftime('%d.%m.%Y')} (ещё {days_left} дн. {hours_left} ч.)"
        sub_icon = "🟢"
    elif sub:
        sub_str = f"{sub.strftime('%d.%m.%Y')} — истекла"
        sub_icon = "🔴"
    else:
        sub_str, sub_icon = "нет", "🔴"

    # Данные Marzban
    traffic_str = online_str = mz_status = "—"
    if user.marzban_username:
        try:
            mz = await marzban.get_user(user.marzban_username)
            used = mz.get("used_traffic", 0)
            traffic_str = f"{used / 1_073_741_824:.2f} ГБ"
            mz_status = mz.get("status", "—")
            oa = mz.get("online_at")
            if oa:
                diff = int(now.timestamp()) - oa
                if diff < 60:
                    online_str = "🟢 Онлайн сейчас"
                elif diff < 3600:
                    online_str = f"🕐 {diff // 60} мин. назад"
                else:
                    online_str = _fmt(datetime.utcfromtimestamp(oa)) + " UTC"
            else:
                online_str = "никогда"
        except Exception as e:
            traffic_str = f"ошибка ({e})"

    uname = f"@{user.username}" if user.username else "—"
    ref = f"<code>{user.referrer_id}</code>" if user.referrer_id else "нет"
    ban_str = "🚫 <b>ЗАБЛОКИРОВАН</b>" if user.is_banned else "✅ активен"
    ref_days = getattr(user, "extra_days_granted", 0) or 0

    # Устройства из БД
    devices_str = ""
    if session:
        try:
            dev_result = await session.execute(
                select(Device).where(
                    Device.telegram_id == user.telegram_id,
                    Device.is_active.is_(True),
                ).order_by(Device.slot)
            )
            devs = dev_result.scalars().all()
            if devs:
                dev_lines = "\n".join(
                    f"  {i + 1}. <code>{d.marzban_username}</code> — {d.name}"
                    for i, d in enumerate(devs)
                )
                devices_str = f"\n<code>{sep}</code>\n📱 <b>Устройства ({len(devs)}/3):</b>\n{dev_lines}"
        except Exception:
            pass

    return (
        f"👤 <b>Досье пользователя</b>\n"
        f"<code>{sep}</code>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: {uname}\n"
        f"📝 Имя: {html.escape(user.full_name or '—')}\n"
        f"📅 Регистрация: {_fmt(user.created_at)}\n"
        f"🔒 Статус: {ban_str}\n"
        f"<code>{sep}</code>\n"
        f"{sub_icon} <b>Подписка:</b> {sub_str}\n"
        f"🔗 Marzban: <code>{user.marzban_username or '—'}</code>\n"
        f"⚙️ VPN статус: <b>{mz_status}</b>\n"
        f"📡 Трафик: <b>{traffic_str}</b>\n"
        f"🕐 Последний онлайн: <b>{online_str}</b>\n"
        f"<code>{sep}</code>\n"
        f"💰 <b>Финансы:</b>\n"
        f"⭐ Оплачено Stars: <b>{user.total_stars_paid or 0} ⭐</b>\n"
        f"👥 Дней получено за рефералов: <b>{ref_days}</b>\n"
        f"<code>{sep}</code>\n"
        f"👥 <b>Партнёрка:</b>\n"
        f"🎁 Триал: {'использован ✅' if user.trial_used else 'не использован'}\n"
        f"👤 Рефералов привёл: <b>{user.referral_count}</b>\n"
        f"📎 Пришёл от: {ref}"
        f"{devices_str}"
    )


async def _do_ban(msg: Message, user: User, session: AsyncSession) -> None:
    user.is_banned = True
    await set_vpn_enabled(user, session, False)
    await session.commit()
    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    await msg.answer(
        f"🚫 <b>{uname}</b> (<code>{user.telegram_id}</code>) заблокирован.\n"
        "VPN-доступ отключён в Marzban.",
        parse_mode="HTML",
    )
    # Уведомить пользователя о блокировке
    try:
        await msg.bot.send_message(
            user.telegram_id,
            f"🚫 <b>Ваш аккаунт заблокирован в STAR VPN.</b>\n\n"
            f"Причина: нарушение Политики конфиденциальности сервиса.\n\n"
            f"📄 <a href=\"{settings.site_url.rstrip('/')}/privacy\">Политика конфиденциальности STAR VPN</a>\n\n"
            f"По вопросам разблокировки обратитесь в поддержку: {settings.support_username}",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def _do_unban(msg: Message, user: User, session: AsyncSession) -> None:
    user.is_banned = False
    if user.subscription_expires_at and user.subscription_expires_at > datetime.utcnow():
        await set_vpn_enabled(user, session, True)
    await session.commit()
    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    await msg.answer(
        f"✅ <b>{uname}</b> разблокирован. VPN-доступ восстановлен.",
        parse_mode="HTML",
    )
    try:
        await msg.bot.send_message(
            user.telegram_id,
            "✅ Ваш аккаунт STAR VPN разблокирован.",
        )
    except Exception:
        pass


async def _do_grant(msg: Message, user: User, days: int, session: AsyncSession) -> None:
    # Та же логика, что при оплате: продлевает все устройства (раньше —
    # только старый основной аккаунт), включает их и сдвигает дату в БД.
    from bot.handlers.payment import _grant_subscription
    await _grant_subscription(user, days, session)

    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    await msg.answer(
        f"✅ <b>{uname}</b> — подписка на <b>{days} дней</b> выдана.\n"
        f"Действует до: <b>{user.subscription_expires_at.strftime('%d.%m.%Y')}</b>",
        parse_mode="HTML",
    )
    try:
        await msg.bot.send_message(
            user.telegram_id,
            f"🎁 <b>Вам выдана подписка на {days} дней!</b>\n"
            "Открой 👤 Профиль → 🔗 Моё подключение.",
            parse_mode="HTML",
        )
    except Exception:
        pass


async def _do_gadgets(msg: Message, user: User) -> None:
    uname = f"@{user.username}" if user.username else str(user.telegram_id)
    if not user.marzban_username:
        await msg.answer(f"📱 <b>{uname}</b> — VPN-аккаунт не создан.", parse_mode="HTML")
        return

    try:
        mz = await marzban.get_user(user.marzban_username)
    except Exception as e:
        await msg.answer(f"❌ Marzban: <code>{e}</code>", parse_mode="HTML")
        return

    oa = mz.get("online_at")
    used = mz.get("used_traffic", 0)
    status = mz.get("status", "?")
    exp = mz.get("expire")
    now_ts = int(datetime.utcnow().timestamp())

    if oa:
        diff = now_ts - oa
        mins = diff // 60
        if mins < 5:
            online_str = f"🟢 Онлайн прямо сейчас ({mins} мин. назад)"
        elif mins < 60:
            online_str = f"🕐 {mins} мин. назад"
        else:
            online_str = _fmt(datetime.utcfromtimestamp(oa)) + " UTC"
    else:
        online_str = "нет данных"

    status_map = {
        "active": "🟢 Активен", "disabled": "🔴 Отключён",
        "expired": "🟡 Истёк",  "limited":  "🟠 Лимит трафика",
    }
    exp_str = datetime.utcfromtimestamp(exp).strftime("%d.%m.%Y") if exp else "—"

    await msg.answer(
        f"📱 <b>Активность: {uname}</b>\n\n"
        f"🔌 Статус VPN: {status_map.get(status, status)}\n"
        f"🕐 Последний онлайн: {online_str}\n"
        f"📡 Скачано: <b>{used / 1_073_741_824:.2f} ГБ</b>\n"
        f"📅 Подписка до: <b>{exp_str}</b>\n\n"
        "<i>ℹ️ Протокол VLESS Reality не передаёт тип устройства — "
        "это гарантия анонимности.</i>",
        parse_mode="HTML",
    )


async def _do_stats(msg: Message, session: AsyncSession) -> None:
    try:
        now = datetime.utcnow()
        total  = (await session.execute(select(func.count()).select_from(User))).scalar_one()
        trial  = (await session.execute(select(func.count()).where(User.trial_used.is_(True)))).scalar_one()
        active = (await session.execute(
            select(func.count()).where(User.subscription_expires_at > now)
        )).scalar_one()
        banned = (await session.execute(select(func.count()).where(User.is_banned.is_(True)))).scalar_one()
        stars_raw = (await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "paid")
        )).scalar_one()
        stars = int(stars_raw) if stars_raw is not None else 0
        pays   = (await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "paid")
        )).scalar_one()
        ref_days_total = int((await session.execute(
            select(func.sum(User.extra_days_granted))
        )).scalar_one() or 0)
    except Exception as e:
        await _err(msg, e)
        return

    # Онлайн-счётчик из Marzban (опционально, не блокирует если недоступен)
    online_count = 0
    try:
        all_mz = await marzban.get_all_users()
        now_ts = now.timestamp()
        online_count = sum(
            1 for u in all_mz
            if u.get("online_at") and (now_ts - u["online_at"]) < 300
        )
    except Exception:
        online_count = -1  # -1 = данные недоступны

    online_str = f"<b>{online_count}</b>" if online_count >= 0 else "<i>н/д</i>"

    await msg.answer(
        f"📊 <b>Статистика STAR VPN</b>\n\n"
        f"👤 Всего пользователей: <b>{total}</b>\n"
        f"🎁 Использовали триал: <b>{trial}</b>\n"
        f"✅ Активных подписок: <b>{active}</b>\n"
        f"🟢 Онлайн прямо сейчас: {online_str}\n"
        f"🚫 Забаненных: <b>{banned}</b>\n\n"
        f"⭐ Заработано Stars: <b>{stars} ⭐</b> ({pays} платежей)\n"
        f"👥 Дней начислено за рефералов: <b>{ref_days_total}</b>",
        parse_mode="HTML",
    )


async def _do_payments(msg: Message, session: AsyncSession) -> None:
    """Последние 10 успешных платежей из БД."""
    try:
        result = await session.execute(
            select(Payment)
            .where(Payment.status == "paid")
            .order_by(Payment.paid_at.desc())
            .limit(10)
        )
        payments = result.scalars().all()
    except Exception as e:
        await _err(msg, e)
        return

    if not payments:
        await msg.answer("📋 Платежей пока нет.")
        return

    lines = []
    for p in payments:
        date_str = p.paid_at.strftime("%d.%m %H:%M") if p.paid_at else "—"
        lines.append(
            f"• <code>{p.telegram_id}</code> — <b>{int(p.amount)} ⭐</b> [{date_str}]"
        )

    await msg.answer(
        f"📋 <b>Последние {len(payments)} платежей</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


async def _do_status(msg: Message) -> None:
    try:
        await marzban._auth()
        await msg.answer(
            f"✅ <b>Marzban работает</b>\n"
            f"URL: <code>{settings.marzban_url}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        await msg.answer(
            f"❌ <b>Marzban недоступен!</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
