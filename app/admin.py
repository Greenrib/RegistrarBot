import calendar
import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
from app.base import bot_user_data

cb = CallbackData("id", "action", "some_data")

now = datetime.datetime.now()
from_date = now.strftime("%Y.%m.%d")
before_date = now + datetime.timedelta(days=7)
before_date = before_date.strftime("%Y.%m.%d")


class RedactorStates(StatesGroup):
    opened = State()
    show_list = State()
    date_selection = State()


async def open_redactor_menu(message: types.Message = None, state: FSMContext = None,
                             call: types.CallbackQuery = None):
    if message:
        check = dbwork.check_admin(message.from_user.id)
    else:
        check = dbwork.check_admin(call.message.chat.id)

    if not check:
        text = "Это не сработало.\nЕсли вы уверены, что должно сработать, обратитесь к Марку."
        await message.answer(text)
    else:
        await state.update_data(from_date=from_date, before_date=before_date)

        text = "Меню администрирования"

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        buttons = [
            types.InlineKeyboardButton(text="Просмотреть брони",
                                       callback_data=cb.new(action="staff_menu",
                                                            some_data=0))
        ]
        keyboard.add(*buttons)

        await RedactorStates.opened.set()

        if message:
            await message.answer(text, reply_markup=keyboard)
        else:
            await call.message.edit_text(text, reply_markup=keyboard)


async def call_redactor_menu(call: types.CallbackQuery, state: FSMContext):
    await open_redactor_menu(call=call, state=state)


# About staff
async def show_reservation_list(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await RedactorStates.show_list.set()

    fsm_data = await state.get_data()

    from_date = fsm_data['from_date']
    before_date = fsm_data['before_date']

    chosen_reservation = dbwork.get_reservation(from_date, before_date)
    reservation_records = ""
    if chosen_reservation:
        for r in chosen_reservation:
            date = f"{r['date'].day}.{r['date'].month}"
            text = f"{date}  {r['time']} ----- {r['contact']}\n\n"

            reservation_records += text
    else:
        reservation_records = "Броней нет"

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
                                             callback_data=cb.new(action='go_to_rmenu',
                                                                  some_data=1))

    keyboard.row(*time_buttons)
    keyboard.add(back_button)

    if from_date == before_date:
        text = f"Брони на {from_date}"
    else:
        text = f"Брони за период \n{from_date} - {before_date}"

    text += f"\n\n{reservation_records}"

    await call.message.edit_text(text, reply_markup=keyboard)


async def date_selection(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await RedactorStates.date_selection.set()

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
            chosen_date = datetime.datetime(current_year, current_month, day).strftime('%Y.%m.%d')
            day_buttons.append(types.InlineKeyboardButton(text=f'{day}',
                                                          callback_data=cb.new(action=action,
                                                                               some_data=chosen_date)))
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='staff_menu',
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
                chosen_date = datetime.datetime(current_year, number, current_day).strftime('%Y.%m.%d')
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
            chosen_date = datetime.datetime(year, current_month, current_day).strftime('%Y.%m.%d')
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


def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(open_redactor_menu, commands="redactor", state="*")
    # Декоратор для кнопки
    dp.register_callback_query_handler(call_redactor_menu,
                                       cb.filter(action="go_to_rmenu"),
                                       state="*")
    # Меню сотрудников
    dp.register_callback_query_handler(show_reservation_list,
                                       cb.filter(action="staff_menu"),
                                       state="*")

    # Выбор дат
    dp.register_callback_query_handler(date_selection,
                                       cb.filter(action=["day_selection", "month_selection", "year_selection"]),
                                       state="*")
    dp.register_callback_query_handler(set_current_date,
                                       cb.filter(action=["set_from_day", "set_before_day", "set_from_month",
                                                         "set_before_month", "set_from_year", "set_before_year"]),
                                       state="*")


