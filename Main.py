import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from aiohttp import ClientSession

from app.base.config_reader import get_config
from app.main_menu import register_handlers_main_menu
from app.admin import register_handlers_admin
from app.test import register_handlers_test
from app.reservation import register_handlers_reservation

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Главное меню"),
        BotCommand(command="/redactor", description="Меню администрации")
    ]
    await bot.set_my_commands(commands)


async def main(loop):
    # Настройка логирования в stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    logger.error("Starting bot")

    # Объявление и инициализация объектов бота и диспетчера
    bot = Bot(token=get_config("bot", "token"))
    storage = RedisStorage2('localhost', 6379, db=5, pool_size=10, prefix='my_fsm_key')
    dp = Dispatcher(bot, storage=storage, loop=loop)


    # Регистрация хэндлеров
    register_handlers_main_menu(dp)
    register_handlers_admin(dp)
    register_handlers_test(dp)
    register_handlers_reservation(dp)

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    async with ClientSession(loop=loop) as session:
        try:
            await dp.start_polling()
        except asyncio.exceptions.TimeoutError:
            await dp.stop_polling()
        finally:
            await session.close()
            await dp.storage.close()


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(main(event_loop))
