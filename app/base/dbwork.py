import logging
from datetime import datetime
from sys import stderr

import pymysql
from pymysql import cursors
from pymysql import Error

from aiogram.utils.callback_data import CallbackData

from app.base.config_reader import get_config

cb = CallbackData("id", "action", "some_data")

now = datetime.now()

str_date = now.strftime("%Y.%m.%d")
str_time = now.strftime("%H:%M")
str_datetime = now.strftime("%Y.%m.%d %H:%M")

logger = logging.getLogger("Registrar_bot")


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
def add_user(user_id, first_name, last_name, username):
    check_query = f"SELECT id FROM users WHERE `user_id` = {user_id} LIMIT 1"
    check = execute_read_query(get_connection(), check_query, "check")
    if not check:
        query = f"INSERT INTO users(user_id, first_name, last_name, username) " \
                f"VALUES ('{user_id}', '{first_name}', '{last_name}', '{username}')"
        execute_query(get_connection(), query, "new user")


def get_user(user_id):
    query = f"SELECT * FROM users WHERE `user_id` = '{user_id}' LIMIT 1"
    result = execute_read_query(get_connection(), query, "get user")
    if result:
        if result[0]['last_name']:
            full_name = f"{result[0]['first_name']} {result[0]['last_name']}"
            result[0]['full_name'] = full_name
        else:
            result[0]['full_name'] = result[0]['first_name']
        return result[0]
    else:
        return []


def edit_user(user_id, changes: dict):
    query = f"UPDATE users SET "

    counter = 1
    for column, value in changes.items():
        query += f"`{column}` = '{value}'"
        if counter < len(changes):
            query += ','

    query += f"WHERE `user_id` = '{user_id}'"

    execute_query(get_connection(), query, "new user")


def get_staff():
    query = f"SELECT * FROM users WHERE `permissions` != ''"
    result = execute_read_query(get_connection(), query, "get staff")

    return result if result else []


def get_reservation(from_date=None, before_date=None, r_id=None):
    if r_id:
        query = f"SELECT * FROM reservation WHERE `id` = '{r_id}' LIMIT 1"
    else:
        if from_date == before_date:
            time_filter = f"`booked_time` = '{from_date}'"
        else:
            time_filter = f"`booked_time` >= '{from_date}' AND `booked_time` <= '{before_date}'"

        query = f"SELECT * FROM reservation WHERE {time_filter} ORDER BY booked_time"

    result = execute_read_query(get_connection(), query, "get reservation")

    if result:
        return result[0] if r_id else result
    else:
        return False


def get_booked_dates():
    query = f"SELECT DISTINCT booked_time FROM reservation WHERE `booked_time` >= '{str_date}'"
    result = execute_read_query(get_connection(), query, "get booked dates")
    date_list = []
    for r in result:
        t_query = f"SELECT COUNT(booked_time) FROM reservation WHERE `booked_time` = '{r['date']}'"
        t_result = execute_read_query(get_connection(), t_query, "get count booked time")
        if t_result and t_result[0]['COUNT(booked_time)'] >= 5:
            date_list.append(r['booked_time'])
    return date_list


def get_booked_time(chosen_date):
    query = f"SELECT booked_time FROM reservation WHERE `booked_time` = '{chosen_date}'"
    result = execute_read_query(get_connection(), query, "get booked time")
    time_list = []
    if result:
        for r in result:
            time_list.append(r['booked_time'].strftime("%H:%M"))
    return time_list


def saving_reservation(booked_time, contact, photo, comment, creator):
    query = f"INSERT INTO reservation(booked_time, create_time, contact, photo, comment, creator)" \
            f"VALUES ('{booked_time}', '{now}', '{contact}', '{photo}', '{comment}', '{creator}')"

    execute_query(get_connection(), query, "saving reservation")


def delete_reservation(r_id: str):
    query = f"DELETE FROM reservation WHERE `id` ='{r_id}'"
    execute_query(get_connection(), query, "delete reservation")


if __name__ == "__main__":
    pass
