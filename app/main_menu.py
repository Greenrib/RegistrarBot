from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
from app.base import bot_user_data

cb = CallbackData("id", "action", "some_data")
now = datetime.now()


class MenuStates(StatesGroup):
    clean = State()


async def menu_start(message: types.Message, state: FSMContext, edite: bool = False):
    await MenuStates.clean.set()

    if message.from_user.is_bot:
        user_id = message.chat.id
    else:
        user_id = message.from_user.id

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    buttons = [
        types.InlineKeyboardButton(text="Создать бронь",
                                   callback_data=cb.new(action="show_free_dates",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Просмотреть брони",
                                   callback_data=cb.new(action="staff_menu",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Ping",
                                   callback_data=cb.new(action="test",
                                                        some_data=0))
    ]

    text = "*Бот\-Регистратор или типа того\.*\n" \
           "`                       Версия 1\.0`\n\n" \
           "                        Главное меню"

    keyboard.add(*buttons)
    if not edite:
        await message.answer(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        dbwork.add_user(user_id, message.from_user.first_name,
                        message.from_user.last_name)
    else:
        await message.edit_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')


async def call_menu_start(call: types.CallbackQuery, state: FSMContext):
    message = call.message
    if call.data.split(':')[2] == "0":
        await menu_start(message, state)
    else:
        await menu_start(message, state, edite=True)


def register_handlers_main_menu(dp: Dispatcher):
    dp.register_message_handler(menu_start, commands="start", state="*")
    dp.register_callback_query_handler(call_menu_start,
                                       cb.filter(action="go_to_menu"),
                                       state="*")
