from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
from app.main_menu import menu_start

cb = CallbackData("id", "action", "some_data")
now = datetime.now()


class ShiftsStates(StatesGroup):
    shift_closed = State()
    shift_opened = State()


async def open_shift(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    last_day = dbwork.get_last_day()
    last_date = last_day['date'].strftime("%Y.%m.%d")

    dbwork.open_shift(call.from_user.id)
    document_id = dbwork.create_document('Учёт', call.message.chat.id)

    if last_day:
        last_accounting = dbwork.get_documents(last_date, last_date, shift_id=last_day['id'])
        if last_accounting:
            last_records = dbwork.get_records(last_accounting[0]['id'])
            for record in last_records:
                dbwork.inventory_recording(document_id, record['employee_id'], record['for_post'], record['group'],
                                           record['title'], record['count'], record['unit'], record['comment'],
                                           record['photo_url'])

    await menu_start(call.message, edite=True, state=state)


async def close_shift(call: types.CallbackQuery):
    await call.answer()

    dbwork.close_shift(call.from_user.id)


def register_handlers_shifts(dp: Dispatcher):
    dp.register_callback_query_handler(open_shift,
                                       cb.filter(action="open_shift"),
                                       state="*")
    dp.register_callback_query_handler(close_shift,
                                       cb.filter(action="close_shift"),
                                       state="*")
