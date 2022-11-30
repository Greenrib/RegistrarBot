import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
# from app.base import bot_user_data

cb = CallbackData("id", "action", "some_data")

now = datetime.datetime.now()
from_date = now.strftime("%Y.%m.%d")
before_date = now + datetime.timedelta(days=7)
before_date = before_date.strftime("%Y.%m.%d")


class MenuStates(StatesGroup):
    clean = State()


async def menu_start(message: types.Message, state: FSMContext, edite: bool = False):
    await MenuStates.clean.set()
    await state.update_data(from_date=from_date, before_date=before_date)

    user = dbwork.get_user(message.chat.id)
    if user['permissions'] in ['Сотрудник', 'Админ']:
        keyboard = types.InlineKeyboardMarkup(row_width=1)

        buttons = [
            types.InlineKeyboardButton(text="Создать бронь",
                                       callback_data=cb.new(action="show_free_dates",
                                                            some_data=0)),
            types.InlineKeyboardButton(text="Просмотреть брони",
                                       callback_data=cb.new(action="show_reservations",
                                                            some_data=0))
        ]

        text = "*Бот\-Регистратор или типа того\.*\n" \
               "`                       Версия 1\.1`\n\n" \
               "                        Главное меню"

        keyboard.add(*buttons)

        if edite:
            await message.edit_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode='MarkdownV2')
    else:
        text = "В доступе отказано. Обратитесь к администратору"
        if edite:
            await message.edit_text(text)
        else:
            await message.answer(text)


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
