import io
import calendar
from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext

from app.base import dbwork
from app.base.config_reader import get_config
from app.base import bot_user_data
from app import test


cb = CallbackData("id", "action", "some_data")
now = datetime.now()


class InventoryStates(StatesGroup):
    waiting_for_title = State()
    waiting_photo = State()
    processing_photo = State()
    waiting_desc = State()
    processing_desc = State()
    show_inventory = State()
    show_document = State()


"""
async def show_inline_inventory(query: types.InlineQuery):
    query_offset = int(query.offset) if query.offset else 0
    catalog_len = dbwork.get_catalog_len()
    next_offset = query_offset + 1

    if next_offset < catalog_len:
        catalog = dbwork.get_catalog(query_offset, next_offset)
    else:
        catalog = dbwork.get_catalog(query_offset, catalog_len)

    results = await get_inline_results(catalog)

    if next_offset <= catalog_len:
        await query.answer(results, next_offset=str(next_offset), cache_time=0)
    else:
        await query.answer(results, next_offset="", cache_time=0)
"""


async def show_inventory(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    await InventoryStates.show_inventory.set()

    fsm_data = await state.get_data()

    from_date = fsm_data['from_date']
    before_date = fsm_data['before_date']

    current_documents = dbwork.get_documents(from_date, before_date, doc_type=fsm_data['doc_type'])

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    time_buttons = [
        types.InlineKeyboardButton(text=from_date,
                                   callback_data=cb.new(action="day_selection",
                                                        some_data='from')),
        types.InlineKeyboardButton(text=before_date,
                                   callback_data=cb.new(action="day_selection",
                                                        some_data='before'))
    ]
    filters_buttons = [
        types.InlineKeyboardButton(text="Тип",
                                   callback_data=cb.new(action="type_selection",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Записал",
                                   callback_data=cb.new(action="employee_selection",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Принял",
                                   callback_data=cb.new(action="receiver_selection",
                                                        some_data=0))
    ]
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='go_to_menu',
                                                                  some_data=1))

    document_buttons = []
    for document in current_documents:
        record_time = document['recording_date']

        employee = dbwork.get_user(document['employee_id'])
        if document['receiver_id']:
            receiver = dbwork.get_user(document['receiver_id'])
        else:
            receiver = employee

        button_text = f"{record_time} - {document['type']} - {employee['full_name']} {receiver['full_name']}"
        document_buttons.append(types.InlineKeyboardButton(text=button_text,
                                                           callback_data=cb.new(action='show_document',
                                                                                some_data=document['id'])))

    keyboard.row(*time_buttons)
    keyboard.row(*filters_buttons)
    keyboard.add(*document_buttons)
    keyboard.add(back_button)

    if from_date == before_date:
        text = f"Документы на {from_date}"
    else:
        text = f"Документы за период {from_date} - {before_date}"

    await call.message.edit_text(text, reply_markup=keyboard)


async def show_document(call: types.CallbackQuery):
    await call.answer()

    await InventoryStates.show_document.set()

    current_document = dbwork.get_documents(doc_id=call.data.split(':')[2])
    current_records = dbwork.get_records(current_document['id'])

    employee = dbwork.get_user(current_document['employee_id'])
    receiver = dbwork.get_user(current_document['receiver_id'])
    if not receiver:
        receiver['full_name'] = '-----'

    text = f"Документ №{current_document['id']} --- {current_document['type']} --- \n" \
           f"Время создания: {current_document['recording_time']}\n" \
           f"Записал: {employee['full_name']}    Принял: {receiver['full_name']}"

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    filters_buttons = [
        types.InlineKeyboardButton(text="Профессия",
                                   callback_data=cb.new(action="post_selection",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Записал",
                                   callback_data=cb.new(action="employee_selection",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Группа",
                                   callback_data=cb.new(action="group_selection",
                                                        some_data=0)),
        types.InlineKeyboardButton(text="Название",
                                   callback_data=cb.new(action="title_selection",
                                                        some_data=0))
    ]

    record_buttons = []
    for record in current_records:
        record_time = record['recording_date']

        button_text = f"{record_time} - {record['for_post']} - " \
                      f"{record['group']} {record['title']} {record['count']} {record['unit']}"
        record_buttons.append(types.InlineKeyboardButton(text=button_text,
                                                         callback_data=cb.new(action='show_record',
                                                                              some_data=record['id'])))

    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='show_inventory',
                                                                  some_data=1))

    keyboard.row(*filters_buttons)
    keyboard.add(*record_buttons)
    keyboard.add(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def create_document(call: types.CallbackQuery):
    await call.answer()

    new_doc_type = call.data.split(':')[2]

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    if new_doc_type == '0':
        text = "Создание документа...\nВыбери тип"
        buttons = [
            types.InlineKeyboardButton(text="Приход",
                                       callback_data=cb.new(action="create_document",
                                                            some_data="Приход")),
            types.InlineKeyboardButton(text="Расход",
                                       callback_data=cb.new(action="create_document",
                                                            some_data="Расход")),
            types.InlineKeyboardButton(text="Переучёт",
                                       callback_data=cb.new(action="create_document",
                                                            some_data="Переучёт"))
        ]
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='go_to_menu',
                                                                      some_data=1))
    else:
        text = f"Новый документ {new_doc_type}"
        buttons = [
            types.InlineKeyboardButton(text="Создать",
                                       callback_data=cb.new(action="add_record",
                                                            some_data=new_doc_type))
        ]
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='create_document',
                                                                      some_data=0))
    keyboard.row(*buttons)
    keyboard.add(back_button)
    await call.message.edit_text(text, reply_markup=keyboard)


async def save_document(call: types.CallbackQuery):
    await call.answer()

    new_doc_type = call.data.split(':')[2]

    doc_id = dbwork.create_document(new_doc_type, call.message.chat.id)
    call.data = f"id:show_document:{doc_id}"

    await show_document(call)


async def show_record(call: types.CallbackQuery):
    await call.answer()

    record = dbwork.get_inventory_record(call.data.split(':')[2])

    employee = dbwork.get_user(record['employee_id'])
    record_time = record['recording_time']

    text = f"{record_time}\n" \
           f"Записал: {employee['full_name']}\n\n" \
           f"Профессия: {record['for_post']}\nГруппа: {record['group']}\n\n" \
           f"{record['title']} - {record['count']} {record['unit']}\n\n" \
           f"Комментарий: {record['comment']}"

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(text='История изменений',
                                   callback_data=cb.new(action="record_history",
                                                        some_data=0))
        ]
    back_button = types.InlineKeyboardButton(text='Назад',
                                             callback_data=cb.new(action='show_document',
                                                                  some_data=record['document_id']))

    keyboard.row(*buttons)
    keyboard.add(back_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def add_record(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    fsm_data = await state.get_data()
    new_doc_type = call.data.split(':')[2]

    text = f"Новый документ {new_doc_type}"

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    record_buttons = []

    if fsm_data['new_records']:
        last_record = fsm_data['new_records'][-1]
        for record in fsm_data['new_records']:
            button_text = f"{record['for_post']} - {record['group']} " \
                          f"{record['title']} {record['count']} {record['unit']}"
            button = types.InlineKeyboardButton(text=button_text,
                                                callback_data=cb.new(action="",
                                                                     some_data=0))
            record_buttons.append(button)
    else:
        last_record = {'for_post': 'Профессия', 'group': 'Группа', 'title': 'Название',
                       'count': 'Кол.', 'unit': 'шт.', 'comment': 'Комментарий'}

    new_record_buttons = [
        types.InlineKeyboardButton(text=last_record['for_post'],
                                   callback_data=cb.new(action="edit_post",
                                                        some_data=0)),
        types.InlineKeyboardButton(text=last_record['group'],
                                   callback_data=cb.new(action="edit_group",
                                                        some_data=0)),
        types.InlineKeyboardButton(text=last_record['title'],
                                   callback_data=cb.new(action="edit_title",
                                                        some_data=0)),
        types.InlineKeyboardButton(text=last_record['count'],
                                   callback_data=cb.new(action="edit_count",
                                                        some_data=0)),
        types.InlineKeyboardButton(text=last_record['unit'],
                                   callback_data=cb.new(action="edit_unit",
                                                        some_data=0)),
        types.InlineKeyboardButton(text=last_record['comment'],
                                   callback_data=cb.new(action="edit_comment",
                                                        some_data=0))
    ]

    save_button = [
        types.InlineKeyboardButton(text='Добавить запись',
                                   callback_data=cb.new(action='save_record',
                                                        some_data=0)),
        types.InlineKeyboardButton(text='Сохранить документ',
                                   callback_data=cb.new(action='save_document',
                                                        some_data=0))
        ]

    keyboard.row(*record_buttons)
    keyboard.row(*new_record_buttons)
    keyboard.add(*save_button)

    await call.message.edit_text(text, reply_markup=keyboard)


async def get_desc(product):
    desc = f"{product['price']}\n{product['description']}\n{product['composition']}"
    return desc


async def get_inline_results(catalog):
    keyboard = types.InlineKeyboardMarkup(row_width=1)

    buttons = [
        types.InlineKeyboardButton(text="Каталог",
                                   switch_inline_query_current_chat="catalog"),
        types.InlineKeyboardButton(text="В корзину",
                                   callback_data=cb.new(action="add_to_cart",
                                                        some_data=0))
    ]
    keyboard.add(*buttons)

    results = [types.InlineQueryResultArticle(
        id=str(flower['id']),
        thumb_url=flower['file_url'],
        title=flower['title'],
        description=await get_desc(flower),
        input_message_content=types.InputTextMessageContent(message_text=f"[{flower['title']}]({flower['file_url']})",
                                                            parse_mode="MarkdownV2"),
        reply_markup=keyboard
    ) for flower in catalog]

    return results


async def date_selection(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

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
            if current_year == now.year and current_month == now.month and day > now.day:
                break
            else:
                chosen_date = datetime(current_year, current_month, day).strftime('%Y.%m.%d')
                day_buttons.append(types.InlineKeyboardButton(text=f'{day}',
                                                              callback_data=cb.new(action=action,
                                                                                   some_data=chosen_date)))
        back_button = types.InlineKeyboardButton(text='Назад',
                                                 callback_data=cb.new(action='show_inventory',
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
        for year in range(now.year-3, now.year+1):
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
        await show_inventory(call, state)
    else:
        call.data = f'id:day_selection:{date_to_selection}'
        await date_selection(call, state)


# About inventory
async def wait_product_photo(call: types.CallbackQuery = None, message: types.Message = None):
    await call.answer()

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    text = "Кидай фото товара.\n\n" \
           "Размер до 5Мб 1080 * 1080"

    buttons = [
        types.InlineKeyboardButton(text="Назад",
                                   callback_data=cb.new(action="go_to_rmenu",
                                                        some_data=0))
    ]
    keyboard.add(*buttons)

    await InventoryStates.waiting_photo.set()
    if not message:
        await call.message.edit_text(text, reply_markup=keyboard)
    else:
        text = "Размер до 5Мб 1080 * 1080"
        await message.answer(text, reply_markup=keyboard)


async def processing_product_photo(message: types.Message, state: FSMContext):
    if message.content_type != 'photo':
        await message.answer('Это не фото.\nПопробуй еще раз. Или вернись назад.')
        await wait_product_photo(message=message)
    else:
        await InventoryStates.processing_photo.set()
        await state.update_data(file_id=message.photo[0].file_id)
        await wait_product_desc(message=message)


async def wait_product_desc(call: types.CallbackQuery = None, message: types.Message = None):
    await call.answer()

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton(text="Назад",
                                   callback_data=cb.new(action="add_product",
                                                        some_data=0))
    ]
    keyboard.add(*buttons)
    await InventoryStates.waiting_desc.set()

    if message:
        text = "Отлично.\nТеперь отправь описание.\nНовые данные в новой строке\n\n" \
               "Название\nЦена\nОписание\nКомпозиция"
        await message.answer(text, reply_markup=keyboard)
    elif call:
        text = "Отправь описание.\nНовые данные в новой строке\n\n" \
               "Название\nЦена\nОписание\nКомпозиция"
        await call.message.edit_caption(text, reply_markup=keyboard)


async def processing_product_desc(message: types.Message, state: FSMContext):
    if message.content_type != 'text':
        await message.answer('Нужно текстом.\nПопробуй еще раз. Или вернись назад.')
        await wait_product_desc(message=message)
    else:
        file_data = await state.get_data()

        clear_desc = message.text
        group_desc = clear_desc.split('\n')
        if len(group_desc) < 4:
            await message.answer('Все поля должны быть заполнены.\nЕсли не хочешь заполнять поле,'
                                 'просто оставь пустую строку.')
            await wait_product_desc(message=message)
        else:
            done_desc = f"{group_desc[0]}\n{group_desc[1]}\n{group_desc[2]}\n{group_desc[3]}"
            await state.update_data(desc=group_desc)

            text = "Так выглядить новый продукт. Нажми \"Сохранить\", если всё в порядке"

            keyboard = types.InlineKeyboardMarkup(row_width=1)
            buttons = [
                types.InlineKeyboardButton(text="Назад",
                                           callback_data=cb.new(action="go_to_wait_desc",
                                                                some_data=0)),
                types.InlineKeyboardButton(text="Сохранить",
                                           callback_data=cb.new(action="save_product",
                                                                some_data=0))
            ]
            keyboard.add(*buttons)

            await InventoryStates.processing_desc.set()
            await message.answer(text)
            await message.answer_photo(file_data['file_id'], caption=done_desc, reply_markup=keyboard)


async def save_product(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    file_data = await state.get_data()

    b = io.BytesIO()
    await call.message.photo[-1].download(destination_file=b)

    response_file_data = dbwork.upload_photo(b, file_data['desc'][0])

#    dbwork.add_product(file_data['desc'], response_file_data['data']['url'], response_file_data['data']['url_viewer'])


def register_handlers_inventory(dp: Dispatcher):
    @dp.inline_handler(state="*")
    async def redirect(query: types.InlineQuery):
        if query.query == 'catalog':
            pass
        elif query.query == 'test':
            await test.test_inline(query)

    dp.register_callback_query_handler(show_inventory,
                                       cb.filter(action="show_inventory"),
                                       state="*")

    dp.register_callback_query_handler(show_document,
                                       cb.filter(action="show_document"),
                                       state="*")
    dp.register_callback_query_handler(create_document,
                                       cb.filter(action="create_document"),
                                       state="*")
    dp.register_callback_query_handler(save_document,
                                       cb.filter(action="save_document"),
                                       state="*")

    dp.register_callback_query_handler(show_record,
                                       cb.filter(action="show_record"),
                                       state="*")
    dp.register_callback_query_handler(add_record,
                                       cb.filter(action="add_record"),
                                       state="*")

    dp.register_callback_query_handler(date_selection,
                                       cb.filter(action=["day_selection", "month_selection", "year_selection"]),
                                       state="*")
    dp.register_callback_query_handler(set_current_date,
                                       cb.filter(action=["set_from_day", "set_before_day", "set_from_month",
                                                         "set_before_month", "set_from_year", "set_before_year"]),
                                       state="*")

    # Добавление товара
    dp.register_callback_query_handler(wait_product_photo,
                                       cb.filter(action="add_inventory"),
                                       state="*")
    dp.register_message_handler(processing_product_photo, state=InventoryStates.waiting_photo,
                                content_types=get_config('telegram', 'content_types'))
    dp.register_message_handler(processing_product_desc, state=InventoryStates.waiting_desc)
    dp.register_callback_query_handler(wait_product_desc,
                                       cb.filter(action="go_to_wait_desc"),
                                       state=InventoryStates.processing_desc)
    dp.register_callback_query_handler(save_product,
                                       cb.filter(action="save_product"),
                                       state=InventoryStates.processing_desc)
