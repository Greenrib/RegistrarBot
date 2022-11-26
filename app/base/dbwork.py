import io
import logging
from datetime import datetime, timedelta, time
from sys import stderr
from base64 import b64encode
from requests import post
from json import loads

import pymysql
from pymysql import cursors
from pymysql import Error

from aiogram.utils.callback_data import CallbackData

from app.base.config_reader import get_config

cb = CallbackData("id", "action", "some_data")

now = datetime.now()

str_date = now.strftime("%Y.%m.%d")
str_time = now.strftime("%H:%M:00")
str_datetime = now.strftime("%Y.%m.%d %H:%M:00")

logger = logging.getLogger("PGOD_bot")


formatter = logging.Formatter(
    '%(asctime)s (%(filename)s:%(lineno)d %(threadName)s) %(levelname)s - %(name)s\n'
    '%(message)s'
)

console_output_handler = logging.StreamHandler(stderr)
console_output_handler.setFormatter(formatter)
logger.addHandler(console_output_handler)

logging.basicConfig(format='%(asctime)s (%(filename)s:%(lineno)d '
                           '%(threadName)s) %(levelname)s - %(name)s\n'
                           '%(message)s',
                    level=logging.INFO)


# Общие функции

# Создаем соединение
def get_connection():
    try:
        connect = pymysql.connect(
            host=get_config("db", "host"),
            user=get_config("db", "user"),
            password=get_config("db", "password"),
            db=get_config("db", "name"),
            cursorclass=cursors.DictCursor
        )

        logger.debug("Connection to Database successful")
        return connect
    except Error as e:
        logger.exception(e)


# Общая функция запроса
def execute_query(connect, query, log):
    cursor = connect.cursor()
    try:
        cursor.execute(query)
        connect.commit()
        logger.debug(f"Execute successful_{log}")
    except Error as e:
        logger.exception(f"In {log} The error '{e}' occurred")
    finally:
        connect.close()


# Функция чтения записей
def execute_read_query(connect, query, log):
    cursor = connect.cursor()
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        logger.debug(f"Read successful_{log}")
        return result
    except Error as e:
        logger.exception(f"In {log} The error '{e}' occurred")
    finally:
        connect.close()


# Функции для работы с пользователями

# Запись нового пользователя
def add_user(user_id, first_name, last_name):
    check_query = f"SELECT id FROM users WHERE `user_id` = {user_id} LIMIT 1"
    check = execute_read_query(get_connection(), check_query, "check")
    if not check:
        query = f"INSERT INTO users(user_id, first_name, last_name) VALUES ('{user_id}'," \
                f" '{first_name}', '{last_name}')"
        execute_query(get_connection(), query, "new user")


def get_user(user_id):
    query = f"SELECT * FROM users WHERE `user_id` = '{user_id}' LIMIT 1"
    result = execute_read_query(get_connection(), query, "get user")
    if result:
        full_name = f"{result[0]['first_name']} {result[0]['last_name']}"
        result[0]['full_name'] = full_name
        return result[0]
    else:
        return None


def get_staff():
    query = f"SELECT * FROM users WHERE `post` != ''"
    result = execute_read_query(get_connection(), query, "get staff")
    if result:
        return result
    else:
        return False


def check_admin(user_id):
    query = f"SELECT isadmin FROM users WHERE `user_id` = '{user_id}'"
    result = execute_read_query(get_connection(), query, "check admins")
    if not result:
        return False
    else:
        return True if result[0]['isadmin'] else False


def get_reservation(from_date=None, before_date=None, user_id=None):
    if user_id:
        query = f"SELECT * FROM reservation WHERE `user_id` = '{user_id}' LIMIT 1"
    else:
        if from_date == before_date:
            time_filter = f"`date` = '{from_date}'"
        else:
            time_filter = f"`date` >= '{from_date}' AND `date` <= '{before_date}'"

        query = f"SELECT * FROM reservation WHERE {time_filter} ORDER BY date, time"

    result = execute_read_query(get_connection(), query, "get documents")

    if result:
        return result if not user_id else result[0]
    else:
        return False


def get_booked_dates():
    query = f"SELECT DISTINCT date FROM reservation WHERE `date` >= '{str_date}'"
    result = execute_read_query(get_connection(), query, "get booked date")
    date_list = []
    for r in result:
        t_query = f"SELECT COUNT(time) FROM reservation WHERE `date` = '{r['date']}'"
        t_result = execute_read_query(get_connection(), t_query, "get count booked time")
        if t_result and t_result[0]['COUNT(time)'] >= 5:
            date_list.append(r['date'])
    return date_list


def get_booked_time(chosen_date):
    query = f"SELECT time FROM reservation WHERE `date` = '{chosen_date}'"
    result = execute_read_query(get_connection(), query, "get booked time")
    time_list = []
    if result:
        for r in result:
            time_list.append(str(r['time']))
    return time_list


def get_inventory_record(record_id):
    query = f"SELECT * FROM records WHERE `id` = '{record_id}' LIMIT 1"
    result = execute_read_query(get_connection(), query, "get inventory record")
    return result[0]


def saving_reservation(user_id, date, r_time, contact, photo):
    query = f"INSERT INTO reservation(date, time, user_id, contact, photo)" \
            f"VALUES ('{date}', '{r_time}', '{user_id}', '{contact}', '{photo}')"

    execute_query(get_connection(), query, "saving reservation")


def get_last_day():
    query = f"SELECT id, date FROM shifts ORDER BY id DESC LIMIT 1"
    result = execute_read_query(get_connection(), query, "get last day")
    return result[0]


def create_document(doc_type, employee_id, comment=None):
    query = f"INSERT INTO documents " \
            f"SET `shift_id` = (SELECT id FROM shifts WHERE `date` = '{str_date}' LIMIT 1), " \
            f"`recording_date` = '{str_date}', `recording_time` = '{str_datetime}', " \
            f"`type` = '{doc_type}', `employee_id` = '{employee_id}', `comment` = '{comment}'"
    execute_query(get_connection(), query, "create document")

    return_query = "SELECT id FROM documents ORDER BY id DESC LIMIT 1"
    doc_id = execute_read_query(get_connection(), return_query, "return document id")
    return doc_id[0]['id']


def upload_photo(b: io.BytesIO, name):
    key = get_config('imgbb', 'api_key')

    image_hash = b64encode(b.getvalue()).decode("utf-8")

    data = {'image': image_hash,
            'name': name}

    response = post(f'https://api.imgbb.com/1/upload?key={key}',
                    data=data)
    dict_response = loads(response.text)
    return dict_response


def get_shift(user_id):
    query = f"SELECT opening_time, closing_time FROM shifts WHERE `user_id` = '{user_id}' " \
            f"AND `date` = '{str_date}'"
    result = execute_read_query(get_connection(), query, "get shift")
    return result


def open_shift(user_id):
    query = f"INSERT INTO shifts(date, user_id, opening_time)" \
            f"VALUES ('{str_date}', '{user_id}', '{str_datetime}')"
    execute_query(get_connection(), query, "open_shift")


def close_shift(user_id):
    query = f"UPDATE shifts SET `closing_time` = '{str_datetime}' WHERE `user_id` = '{user_id}'" \
            f"AND `date` = '{str_date}'"
    execute_query(get_connection(), query, "close shift")


if __name__ == "__main__":
    pass
