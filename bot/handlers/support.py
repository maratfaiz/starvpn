"""
Двусторонняя переписка по заявке в поддержку прямо в Telegram.

Заявки создаются на сайте (/support) или из личного кабинета — бот их не
создаёт напрямую (см. bot/handlers/start.py::support_handler, который
теперь просто ведёт на форму). Но когда админ отвечает через админку
(bot/api.py::web_ticket_reply), пользователю с реальным telegram_id
приходит сообщение с кнопкой «✍️ Ответить» — она включает
SupportForm.waiting_reply, и следующее текстовое сообщение уходит в тред
заявки как есть, без отдельной команды.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.support_ticket import SupportTicket
from bot.models.support_ticket_message import SupportTicketMessage
from bot.states.payment_states import SupportForm

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("ticket_reply:"))
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    ticket_id = int(callback.data.split(":", 1)[1])
    ticket = await session.get(SupportTicket, ticket_id)
    if not ticket:
        await callback.answer("Заявка не найдена — похоже, устарела.", show_alert=True)
        return

    await state.set_state(SupportForm.waiting_reply)
    await state.update_data(ticket_id=ticket_id)
    await callback.answer()
    await callback.message.answer(
        f"✍️ Напиши сообщение одним текстом — оно уйдёт в заявку «S-{ticket_id:06d}»."
    )


@router.message(SupportForm.waiting_reply)
async def ticket_reply_capture(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    ticket_id = data.get("ticket_id")
    await state.clear()

    ticket = await session.get(SupportTicket, ticket_id) if ticket_id else None
    if not ticket:
        await message.answer("Не нашли эту заявку — попробуй оформить новую на сайте.")
        return

    text = (message.text or message.caption or "").strip()
    if not text:
        await message.answer("Не получилось прочитать сообщение — пришли, пожалуйста, текстом.")
        return

    session.add(SupportTicketMessage(ticket_id=ticket.id, sender="user", body=text[:4000]))
    ticket.status = "open"
    ticket.last_message_at = datetime.utcnow()
    ticket.last_message_sender = "user"
    await session.commit()

    await message.answer(f"✅ Отправлено в заявку «S-{ticket.id:06d}» — ответим здесь же.")
