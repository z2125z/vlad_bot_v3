import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import admin, user, mailing_constructor
import config
from services.logger import logger

# Отключаем логирование aiogram, чтобы использовать наше
logging.getLogger('aiogram').setLevel(logging.WARNING)

async def main():
    logger.info("Bot starting...")
    
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(mailing_constructor.router)  
    dp.include_router(user.router)
    
    logger.info("Bot started successfully")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())