import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import admin, user, mailing_constructor  # Добавлен импорт mailing_constructor
import config


# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(mailing_constructor.router)  
    dp.include_router(user.router)


    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())