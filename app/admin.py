import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
from app.base.config_reader import get_config
# from app.base import bot_user_data

cb = CallbackData("id", "action", "some_data")

now = datetime.datetime.now()


class RedactorStates(StatesGroup):
    opened = State()
    request_for_staff = State()
    processing_staff = State()


async def open_redactor_menu(message: types.Message, state: FSMContext):
    await RedactorStates.opened.set()
    user = dbwork.get_user(message.chat.id)

    if user['permissions'] == "Админ":
        text = "Меню администрирования"

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [
            types.InlineKeyboardButton(text="Сотрудники",
                                       callback_data=cb.new(action="show_staff",
                                                            some_data=0))
        ]
        keyboard.add(*buttons)

        await message.answer(text, reply_markup=keyboard)

    else:
        text = "Это не сработало.\nЕсли вы уверены, что должно сработать, обратитесь к Марку."
        await message.answer(text)


async def call_redactor_menu(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await open_redactor_menu(message=call.message, state=state)


# About staff
async def show_staff(call: types.CallbackQuery):
    await call.answer()

    staff_list = dbwork.get_staff()
    staff_button = []

    if staff_list:
        for staff in staff_list:
            b_text = f"  @{staff['username']} ----- {staff['permissions']}"

            staff_button.append(
                types.InlineKeyboardButton(text=b_text,
                                           callback_data=cb.new(action="open_staff",
                                                                some_data=staff['user_id']))
            )
    else:
        staff_button.append(types.InlineKeyboardButton(text="Пока нет сотрудников",
                                                       callback_data=cb.new(action="",
                                                                            some_data=0)))
    add_staff = types.InlineKeyboardButton(text="Добавить",
                                           callback_data=cb.new(action="add_staff",
                                                                some_data=0))
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='go_to_rmenu',
                                                                  some_data=1))

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*staff_button)
    keyboard.add(add_staff)
    keyboard.add(back_button)

    await call.message.edit_text("Список сотрудников", reply_markup=keyboard)


async def request_for_staff(call: types.CallbackQuery):
    await call.answer()
    await call.message.delete()
    await call.message.answer("Перешли любое сообщение от сотрудника")
    await RedactorStates.request_for_staff.set()


async def processing_staff(message: types.Message = None, state: FSMContext = None):
    await RedactorStates.processing_staff.set()

    dbwork.add_user(user_id=message.forward_from.id,
                    first_name=message.forward_from.first_name,
                    last_name=message.forward_from.last_name,
                    username=message.forward_from.username)
    await state.update_data(new_staff_id=message.forward_from.id)

    text = f"Новый сотрудник:\n\n{message.forward_from.full_name} | @{message.forward_from.username}\n\n" \
           f"Укажи уровень доступа"

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    buttons = [
        types.InlineKeyboardButton(text="Сотрудник",
                                   callback_data=cb.new(action="set_permissions",
                                                        some_data='Сотрудник')),
        types.InlineKeyboardButton(text="Админ",
                                   callback_data=cb.new(action="set_permissions",
                                                        some_data='Админ'))
        ]
    keyboard.add(*buttons)

    await message.answer(text, reply_markup=keyboard)


async def save_staff(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    fsm_data = await state.get_data()
    dbwork.edit_user(fsm_data['new_staff_id'], {'permissions': call.data.split(':')[2]})

    await call.message.edit_text("Сотрудник добавлен")
    await open_redactor_menu(call.message, state)


async def open_staff(call: types.CallbackQuery):
    await call.answer()

    staff_id = call.data.split(':')[2]
    staff = dbwork.get_user(staff_id)

    buttons = [
        types.InlineKeyboardButton(text='Удалить',
                                   callback_data=cb.new(action="delete_staff",
                                                        some_data=staff_id))
    ]
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='show_staff',
                                                                  some_data=0))

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.row(*buttons)
    keyboard.add(back_button)

    text = f"Имя -- {staff['full_name']} | @{staff['username']}\n\n" \
           f"Уровень доступа -- {staff['permissions']}"

    await call.message.edit_text(text, reply_markup=keyboard)


async def delete_staff(call: types.CallbackQuery):
    await call.answer()

    staff_id = call.data.split(':')[2]
    dbwork.edit_user(staff_id, {'permissions': ''})

    await show_staff(call)


def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(open_redactor_menu, commands="redactor", state="*")
    # Декоратор для кнопки
    dp.register_callback_query_handler(call_redactor_menu,
                                       cb.filter(action="go_to_rmenu"),
                                       state="*")

    # Добавление сотрудника
    dp.register_callback_query_handler(request_for_staff,
                                       cb.filter(action="add_staff"),
                                       state='*')
    dp.register_message_handler(processing_staff,
                                content_types=get_config('telegram', 'content_types'),
                                state=RedactorStates.request_for_staff)
    dp.register_callback_query_handler(save_staff,
                                       cb.filter(action="set_permissions"),
                                       state=RedactorStates.processing_staff)

    # Просмотр сотрудников
    dp.register_callback_query_handler(show_staff,
                                       cb.filter(action="show_staff"),
                                       state='*')
    dp.register_callback_query_handler(open_staff,
                                       cb.filter(action="open_staff"),
                                       state='*')

    # Удаление сотрудников
    dp.register_callback_query_handler(delete_staff,
                                       cb.filter(action="delete_staff"),
                                       state='*')

