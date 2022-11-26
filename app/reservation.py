import calendar
import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app import main_menu
from app.base import dbwork
from app.base.config_reader import get_config
from app.base import bot_user_data
from app import test

cb = CallbackData("id", "action", "some_data")
now = datetime.datetime.now()


class ReservationStates(StatesGroup):
    show_dates = State()
    show_times = State()
    confirmation = State()
    request_for_name = State()
    name_processing = State()
    request_for_photo = State()
    photo_processing = State()
    saving = State()


async def show_free_dates(call: types.CallbackQuery, state: FSMContext, month_plus=False):
    await call.answer()
    await ReservationStates.show_dates.set()

    fsm_data = await state.get_data()

    text = "Выбери дату"

    dates_buttons = get_calendar(month_plus)
    back_button = types.InlineKeyboardButton(text="Назад",
                                             callback_data=cb.new(action="go_to_menu",
                                                                  some_data=1))
    month_switch_buttons = [types.InlineKeyboardButton(text="➡",
                                                       callback_data=cb.new(action="month_forward",
                                                                            some_data=0)),
                            types.InlineKeyboardButton(text="⬅",
                                                       callback_data=cb.new(action="month_back",
                                                                            some_data=0))
                            ]
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    keyboard.add(*dates_buttons['free'])
    if month_plus:
        keyboard.row(month_switch_buttons[1])
    else:
        keyboard.row(month_switch_buttons[0])
    keyboard.row(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def show_free_time(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.show_times.set()

    text = "Выбери время"

    chosen_date = call.data.split(':')[2]
    await state.update_data(chosen_date=chosen_date)

    booked_time = dbwork.get_booked_time(reverse_date(chosen_date))
    time_buttons = []

    if chosen_date == now.strftime('%d.%m'):
        time_range = range(now.hour+1, 23)
    else:
        time_range = range(10, 23)

    for t in time_range:
        if f'{t}:00:00' not in booked_time:
            time_buttons.append(types.InlineKeyboardButton(text=f'{t}:00',
                                                           callback_data=cb.new(action='time_selected',
                                                                                some_data=t)))
    back_button = types.InlineKeyboardButton(text="Назад",
                                             callback_data=cb.new(action="show_free_dates",
                                                                  some_data=0))
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    keyboard.add(*time_buttons)
    keyboard.row(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def confirmation(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.confirmation.set()

    chosen_time = call.data.split(':')[2] + ':00'
    await state.update_data(chosen_time=chosen_time)

    local_data = await state.get_data()

    text = f"Запись на {local_data['chosen_date']}\nВремя: {local_data['chosen_time']}\n\n" \
           f"Подтверждаем?"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(text="Да",
                                   callback_data=cb.new(action="approval",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Назад",
                                   callback_data=cb.new(action="date_selected",
                                                        some_data=local_data['chosen_date']))
    ]

    keyboard.add(*buttons)

    await call.message.edit_text(text, reply_markup=keyboard)


async def request_for_name(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.request_for_name.set()
    await call.message.delete()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    send_contact = types.KeyboardButton(text="Отправить контакт", request_contact=True)
    keyboard.add(send_contact)

    text = "Отлично. Для связи отправь свой контакт через кнопку или телеграм через @user_name"

    await call.message.answer(text, reply_markup=keyboard)


async def name_processing(message: types.Message, state: FSMContext):
    await ReservationStates.name_processing.set()

    if message.content_type == "contact":
        await state.update_data(contact=message.contact.phone_number, user_id=message.from_user.id)
        await request_for_photo(message,state)
    else:
        await state.update_data(contact=message.text, user_id=message.from_user.id)
        await request_for_photo(message, state)


async def request_for_photo(message: types.Message, state: FSMContext):
    text = "Теперь отправь своё фото в таком-то виде"
    await ReservationStates.request_for_photo.set()

    await message.answer(text, reply_markup=types.ReplyKeyboardRemove())


async def photo_processing(message: types.Message, state: FSMContext):
    await ReservationStates.photo_processing.set()

    if message.content_type == "document":
        await state.update_data(photo=message.document.file_id)
        await saving_reservation(message, state)


async def saving_reservation(message: types.Message, state: FSMContext):
    await ReservationStates.saving.set()

    fsm_data = await state.get_data()
    chosen_date = reverse_date(fsm_data['chosen_date'])
    dbwork.saving_reservation(fsm_data['user_id'], chosen_date, fsm_data['chosen_time'],
                              fsm_data['contact'], fsm_data['photo'])
    text = f"{fsm_data['contact']}\nБудет в {fsm_data['chosen_time']}"
    await message.answer(f"Бронь создана.")
    reservation_message = await message.answer_document(document=fsm_data['photo'], caption=text)
    await reservation_message.send_copy(chat_id=get_config('bot', 'admin'))
    await main_menu.menu_start(message, state)


def get_calendar(month_plus: bool):
    a = calendar.TextCalendar(calendar.MONDAY)
    booked_dates = dbwork.get_booked_dates()

    if month_plus:
        current_month = now.month + 1
    else:
        current_month = now.month

    free_dates_button = []
    booked_dates_button = []

    for date in a.itermonthdates(now.year, current_month):
        if date >= now.date():

            date_button = types.InlineKeyboardButton(text=date.strftime('%d.%m'),
                                                     callback_data=cb.new(action='date_selected',
                                                     some_data=date.strftime('%d.%m')))
            if date in booked_dates:
                booked_dates_button.append(date_button)
            else:
                free_dates_button.append(date_button)
    return {'free': free_dates_button, 'booked': booked_dates_button}


async def month_switch(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data.split(':')[1] == "month_forward":
        await show_free_dates(call, state, month_plus=True)
    else:
        await show_free_dates(call, state)


def reverse_date(date: str):
    split_date = date.split('.')
    reversed_date = f'{now.year}.{split_date[1]}.{split_date[0]}'
    return reversed_date


def register_handlers_reservation(dp: Dispatcher):
    dp.register_callback_query_handler(show_free_dates,
                                       cb.filter(action="show_free_dates"),
                                       state="*")
    dp.register_callback_query_handler(show_free_time,
                                       cb.filter(action="date_selected"),
                                       state="*")
    dp.register_callback_query_handler(confirmation,
                                       cb.filter(action="time_selected"),
                                       state="*")
    dp.register_callback_query_handler(request_for_name,
                                       cb.filter(action="approval"),
                                       state="*")
    dp.register_message_handler(name_processing, content_types=['text', 'contact'],
                                state=ReservationStates.request_for_name)
    dp.register_message_handler(photo_processing, content_types=['document'],
                                state=ReservationStates.request_for_photo)
    dp.register_callback_query_handler(month_switch,
                                       cb.filter(action=['month_forward', 'month_back']),
                                       state="*")
