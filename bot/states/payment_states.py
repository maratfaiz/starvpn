"""FSM states."""

from aiogram.fsm.state import State, StatesGroup


class AdminForm(StatesGroup):
    """Интерактивная админ-панель — ждёт ввода после нажатия кнопки."""
    ban_target        = State()
    unban_target      = State()
    grant_user        = State()
    grant_days        = State()
    userinfo_target   = State()
    gadgets_target    = State()
    message_user      = State()
    message_text      = State()
    broadcast_text    = State()
    broadcast_confirm = State()
    setbalance_user   = State()
    setbalance_amount = State()


class GiftForm(StatesGroup):
    """FSM для подарка подписки другому пользователю."""
    pay_method       = State()  # выбор способа оплаты: Stars или Крипта
    recipient        = State()  # ввод ID или @username получателя
    anon_choice      = State()  # выбор анонимности (inline кнопки)
    personal_message = State()  # необязательное личное сообщение (только Stars)


class DeviceForm(StatesGroup):
    """FSM для добавления нового устройства."""
    name = State()  # пользователь вводит название устройства
