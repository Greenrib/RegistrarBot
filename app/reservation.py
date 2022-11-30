import calendar
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app import main_menu
from app.base import dbwork
from app.base.config_reader import get_config
from app.base import bot_user_data
# from app import test

cb = CallbackData("id", "action", "some_data")
now = datetime.now()


class ReservationStates(StatesGroup):
    show_dates = State()
    show_times = State()
    request_for_contact = State()
    contact_processing = State()
    request_for_comment = State()
    comment_processing = State()
    saving = State()
    show_reservation = State()
    date_selection = State()


async def show_free_dates(call: types.CallbackQuery, month_plus=False):
    await call.answer()
    await ReservationStates.show_dates.set()

    text = "Выбери дату"

    free_dates_buttons = get_calendar(month_plus)

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
    keyboard.add(*free_dates_buttons)

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

    chosen_date = get_datetime(call.data.split(':')[2])

    await state.update_data(chosen_date=call.data.split(':')[2])

    booked_time = dbwork.get_booked_time(chosen_date)
    time_buttons = []

    if chosen_date == now:
        time_range = range(now.hour+1, 23)
    else:
        time_range = range(10, 23)

    for t in time_range:
        if f'{t}:00' not in booked_time:
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


async def request_for_contact(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.request_for_contact.set()

    chosen_time = call.data.split(':')[2] + ':00'

    await state.update_data(chosen_time=chosen_time)
    fsm_data = await state.get_data()

    text = f"Запись на {fsm_data['chosen_date']}\nВремя: {fsm_data['chosen_time']}\n\n" \
           f"Отправь фото файлом и username в описании"

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    back_button = types.InlineKeyboardButton(text="Назад",
                                             callback_data=cb.new(action="date_selected",
                                                                  some_data=fsm_data['chosen_date']))
    keyboard.add(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def contact_processing(message: types.Message, state: FSMContext):
    await ReservationStates.contact_processing.set()

    if message.content_type == "document":
        await state.update_data(photo=message.document.file_id)
        if message.caption:
            await state.update_data(contact=message.caption)

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton(text='Без комментария'))

            await message.answer(f"Добавь комментарий если надо", reply_markup=keyboard)

            await ReservationStates.request_for_comment.set()
        else:
            text = "Ты не добавил имя пользователя в описании, попробуй еще раз"
            await message.answer(text)
    else:
        text = "Надо кинуть файл, попробуй еще раз"
        await message.answer(text)


async def comment_processing(message: types.Message, state: FSMContext):
    await ReservationStates.comment_processing.set()

    if message.content_type == "text":
        if message.text == "Без комментария":
            message.text = " "
        await saving_reservation(message, state)
    else:
        text = "Надо кинуть просто текст, попробуй еще раз"
        await message.answer(text)


async def saving_reservation(message: types.Message, state: FSMContext):
    await ReservationStates.saving.set()

    fsm_data = await state.get_data()
    booked_time = get_datetime(fsm_data['chosen_date'], fsm_data['chosen_time'])

    dbwork.saving_reservation(booked_time=booked_time,
                              contact=fsm_data['contact'],
                              photo=fsm_data['photo'],
                              comment=message.text,
                              creator=message.from_user.username)

    text = f"{fsm_data['contact']}\nБудет в {fsm_data['chosen_time']}\n{message.text}"

    keyboard = types.ReplyKeyboardRemove()
    await message.answer(f"Бронь создана.", reply_markup=keyboard)

    reservation_message = await message.answer_document(document=fsm_data['photo'], caption=text)
    await reservation_message.send_copy(chat_id=get_config('bot', 'admin'))

    await main_menu.menu_start(message, state)


async def show_reservation_list(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.show_reservation.set()

    fsm_data = await state.get_data()

    from_date = fsm_data['from_date']
    before_date = fsm_data['before_date']

    chosen_reservation = dbwork.get_reservation(from_date, before_date)
    reservation_buttons = []
    if chosen_reservation:
        for r in chosen_reservation:
            booked_time = f"{r['booked_time'].strftime('%d.%m -- %H:%M')}"
            b_text = f"{booked_time} ----- {r['contact']}"

            reservation_buttons.append(
                types.InlineKeyboardButton(text=b_text,
                                           callback_data=cb.new(action="open_reservation",
                                                                some_data=r['id']))
            )
    else:
        reservation_buttons.append(types.InlineKeyboardButton(text="Броней нет",
                                                              callback_data=cb.new(action="",
                                                                                   some_data=0)))

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    time_buttons = [
        types.InlineKeyboardButton(text=from_date,
                                   callback_data=cb.new(action="day_selection",
                                                        some_data='from')),
        types.InlineKeyboardButton(text=before_date,
                                   callback_data=cb.new(action="day_selection",
                                                        some_data='before'))
        ]
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='go_to_menu',
                                                                  some_data=1))

    keyboard.row(*time_buttons)
    keyboard.add(*reservation_buttons)
    keyboard.add(back_button)

    if from_date == before_date:
        text = f"Брони на {from_date}"
    else:
        text = f"Брони за период \n{from_date} - {before_date}"

    send = call.data.split(':')[2]
    if send == '1':
        await call.message.delete()
        await call.message.answer(text, reply_markup=keyboard)
    else:
        await call.message.edit_text(text, reply_markup=keyboard)


async def open_reservation(call: types.CallbackQuery):
    await call.answer()
    await call.message.delete()

    r_id = call.data.split(':')[2]

    chosen_reservation = dbwork.get_reservation(r_id=r_id)
    create_time = chosen_reservation['create_time'].strftime("%H:%M")
    booked_time = chosen_reservation['booked_time'].strftime("%H:%M")

    buttons = [
        types.InlineKeyboardButton(text='Удалить',
                                   callback_data=cb.new(action="confirmation_delete",
                                                        some_data=r_id)),
        types.InlineKeyboardButton(text='Редактировать',
                                   callback_data=cb.new(action="edit_reservation",
                                                        some_data=r_id))
    ]
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='show_reservations',
                                                                  some_data=1))

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.row(*buttons)
    keyboard.add(back_button)

    text = f"Бронь №{chosen_reservation['id']} от {create_time}\n\n" \
           f"Записал -- {chosen_reservation['creator']}\n\n" \
           f"Время -- {booked_time}\n" \
           f"Контакт -- {chosen_reservation['contact']}\n" \
           f"Коммент -- {chosen_reservation['comment']}\n"

    await call.message.answer_document(chosen_reservation['photo'], caption=text,
                                       reply_markup=keyboard)


async def confirmation_delete(call: types.CallbackQuery):
    await call.answer()
    await call.message.delete()

    r_id = call.data.split(':')[2]

    buttons = [
        types.InlineKeyboardButton(text='Да',
                                   callback_data=cb.new(action="delete_reservation",
                                                        some_data=r_id)),
        types.InlineKeyboardButton(text='Нет',
                                   callback_data=cb.new(action="open_reservation",
                                                        some_data=r_id))
    ]

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.row(*buttons)

    text = "Точно? Удалиться полностью."

    await call.message.answer(text, reply_markup=keyboard)


async def delete_reservation(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    r_id = call.data.split(':')[2]
    dbwork.delete_reservation(r_id)

    await show_reservation_list(call, state)


async def edit_reservation(call: types.CallbackQuery):
    await call.answer(text="Пока в разработке. Для редактирования удали бронь и создай заново",
                      show_alert=True)


async def date_selection(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ReservationStates.date_selection.set()

    fsm_data = await state.get_data()
    keyboard = types.InlineKeyboardMarkup(row_width=6)

    date_to_selection = call.data.split(':')[2]
    unit_to_selection = call.data.split(':')[1]

    if date_to_selection == 'from':
        current_date = fsm_data['from_date'].split('.')
    else:
        current_date = fsm_data['before_date'].split('.')

    current_year = int(current_date[0])
    current_month = int(current_date[1])
    current_day = int(current_date[2])

    if unit_to_selection == 'day_selection':
        text = "Выбери дату"
        action = f'set_{date_to_selection}_day'

        month_range = calendar.monthrange(current_year, current_month)

        day_buttons = []
        ym_buttons = [types.InlineKeyboardButton(text=f'{current_year}',
                                                 callback_data=cb.new(action='year_selection',
                                                                      some_data=f'{date_to_selection}')),
                      types.InlineKeyboardButton(text=f'{current_date[1]}',
                                                 callback_data=cb.new(action='month_selection',
                                                                      some_data=f'{date_to_selection}'))
                      ]

        for day in range(1, month_range[1] + 1):
            chosen_date = datetime(current_year, current_month, day).strftime('%Y.%m.%d')
            day_buttons.append(types.InlineKeyboardButton(text=f'{day}',
                                                          callback_data=cb.new(action=action,
                                                                               some_data=chosen_date)))
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='show_reservations',
                                                                      some_data=0))

        keyboard.row(*ym_buttons)
        keyboard.add(*day_buttons)
        keyboard.row(back_button)

    elif unit_to_selection == 'month_selection':
        text = "Выбери месяц"
        action = f'set_{date_to_selection}_month'

        months = bot_user_data.months
        month_buttons = []
        for number, title in months.items():
            if current_year == now.year and number > now.month:
                break
            else:
                chosen_date = datetime(current_year, number, current_day).strftime('%Y.%m.%d')
                month_buttons.append(types.InlineKeyboardButton(text=f'{number}: {title}',
                                                                callback_data=cb.new(action=action,
                                                                                     some_data=chosen_date)))
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='day_selection',
                                                                      some_data=date_to_selection))
        keyboard.add(*month_buttons)
        keyboard.row(back_button)
    else:
        text = "Выбери год"
        action = f'set_{date_to_selection}_year'

        year_buttons = []
        for year in range(now.year, now.year+1):
            chosen_date = datetime(year, current_month, current_day).strftime('%Y.%m.%d')
            year_buttons.append(types.InlineKeyboardButton(text=f'{year}',
                                                           callback_data=cb.new(action=action,
                                                                                some_data=chosen_date)))
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='day_selection',
                                                                      some_data=date_to_selection))
        keyboard.add(*year_buttons)
        keyboard.row(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def set_current_date(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    date_to_selection = call.data.split(':')[1].split('_')[1]
    unit_type = call.data.split(':')[1].split('_')[2]
    chosen_date = call.data.split(':')[2]

    if date_to_selection == 'from':
        await state.update_data(from_date=chosen_date)
    else:
        await state.update_data(before_date=chosen_date)

    if unit_type == 'day':
        await show_reservation_list(call, state)
    else:
        call.data = f'id:day_selection:{date_to_selection}'
        await date_selection(call, state)


def get_calendar(month_plus: bool):
    a = calendar.TextCalendar(calendar.MONDAY)
    booked_dates = dbwork.get_booked_dates()

    if month_plus:
        current_month = now.month + 1
    else:
        current_month = now.month

    free_dates_button = []

    for date in a.itermonthdates(now.year, current_month):
        if date >= now.date():
            date_button = types.InlineKeyboardButton(text=date.strftime('%d.%m'),
                                                     callback_data=cb.new(action='date_selected',
                                                     some_data=date.strftime('%d.%m')))
            if date not in booked_dates:
                free_dates_button.append(date_button)
    return free_dates_button


async def month_switch(call: types.CallbackQuery):
    await call.answer()
    if call.data.split(':')[1] == "month_forward":
        await show_free_dates(call, month_plus=True)
    else:
        await show_free_dates(call)


def get_datetime(date: str, time: str = None):
    split_date = date.split('.')
    if time:
        split_time = time.split(':')
        reversed_date = datetime(now.year, int(split_date[1]), int(split_date[0]),
                                 int(split_time[0]))
    else:
        reversed_date = datetime(now.year, int(split_date[1]), int(split_date[0]))

    return reversed_date


def register_handlers_reservation(dp: Dispatcher):
    # Создание брони
    dp.register_callback_query_handler(show_free_dates,
                                       cb.filter(action="show_free_dates"),
                                       state="*")
    dp.register_callback_query_handler(show_free_time,
                                       cb.filter(action="date_selected"),
                                       state="*")
    dp.register_callback_query_handler(request_for_contact,
                                       cb.filter(action="time_selected"),
                                       state="*")

    dp.register_message_handler(contact_processing, content_types=get_config('telegram', 'content_types'),
                                state=[ReservationStates.request_for_contact,
                                       ReservationStates.contact_processing])
    dp.register_message_handler(comment_processing, content_types=get_config('telegram', 'content_types'),
                                state=[ReservationStates.request_for_comment,
                                       ReservationStates.comment_processing])

    # Просмотр броней
    dp.register_callback_query_handler(show_reservation_list,
                                       cb.filter(action="show_reservations"),
                                       state="*")
    dp.register_callback_query_handler(open_reservation,
                                       cb.filter(action="open_reservation"),
                                       state="*")
    # Удаление броней
    dp.register_callback_query_handler(confirmation_delete,
                                       cb.filter(action="confirmation_delete"),
                                       state="*")
    dp.register_callback_query_handler(delete_reservation,
                                       cb.filter(action="delete_reservation"),
                                       state="*")

    # Редактирование броней
    dp.register_callback_query_handler(edit_reservation,
                                       cb.filter(action="edit_reservation"),
                                       state="*")

    # Установка дат для выборки
    dp.register_callback_query_handler(date_selection,
                                       cb.filter(action=["day_selection", "month_selection", "year_selection"]),
                                       state="*")
    dp.register_callback_query_handler(set_current_date,
                                       cb.filter(action=["set_from_day", "set_before_day", "set_from_month",
                                                         "set_before_month", "set_from_year", "set_before_year"]),
                                       state="*")
    # Переключатель месяцев
    dp.register_callback_query_handler(month_switch,
                                       cb.filter(action=['month_forward', 'month_back']),
                                       state="*")
