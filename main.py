import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import admin, user, mailing_constructor
import config
from services.logger import logger
from services.database import db
from services.media_storage import media_storage

async def run_migrations():
    """Запуск миграций при старте"""
    try:
        logger.info("Checking for migrations...")
        
        # Импортируем здесь чтобы избежать циклических импортов
        from migration_universal import run_universal_migration
        
        # Запускаем миграцию
        run_universal_migration()
        logger.info("Migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        # Не падаем, если миграции не сработали - бот продолжит работу

async def periodic_cleanup():
    """Периодическая очистка старых файлов"""
    import time
    
    while True:
        try:
            # Ждем 24 часа
            await asyncio.sleep(24 * 60 * 60)
            
            logger.info("Running periodic media storage cleanup...")
            
            # Очищаем файлы старше 180 дней
            stats = media_storage.cleanup_old_files(days_old=180)
            
            # Логируем статистику
            storage_stats = media_storage.get_storage_stats()
            logger.info(f"Storage stats: {storage_stats['total_files']} files, "
                       f"{storage_stats['total_size_mb']:.2f} MB, "
                       f"oldest: {storage_stats['oldest_file_days']} days")
            
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

async def main():
    """Основная функция запуска бота"""
    try:
        logger.info("=" * 50)
        logger.info("Bot starting...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Admin IDs: {config.ADMIN_IDS}")
        
        # Запуск миграций
        await run_migrations()
        
        # Инициализация бота
        bot = Bot(token=config.BOT_TOKEN)
        
        # Устанавливаем бота в хранилище медиа
        media_storage.set_bot(bot)
        
        # Выводим статистику хранилища при старте
        storage_stats = media_storage.get_storage_stats()
        logger.info(f"Media storage initialized: {storage_stats['total_files']} files, "
                   f"{storage_stats['total_size_mb']:.2f} MB")
        
        dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрация роутеров
        dp.include_router(admin.router)
        dp.include_router(mailing_constructor.router)  
        dp.include_router(user.router)
        
        # Отключаем логирование aiogram, чтобы использовать наше
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
        
        logger.info("Bot started successfully")
        logger.info("=" * 50)
        
        # Запускаем периодическую очистку в фоне
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        # Запуск бота с обработкой ошибок
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise
    finally:
        try:
            # Отменяем задачу очистки
            if 'cleanup_task' in locals():
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Закрываем соединение с базой данных
            db.close()
            logger.info("Database connection closed")
            
            # Очищаем старые файлы в хранилище (180+ дней)
            media_storage.cleanup_old_files(days_old=180)
            logger.info("Media storage cleaned up (180+ days old)")
            
            # Выводим финальную статистику
            final_stats = media_storage.get_storage_stats()
            logger.info(f"Final storage stats: {final_stats['total_files']} files, "
                       f"{final_stats['total_size_mb']:.2f} MB")
            
            # Закрываем сессию бота
            if 'bot' in locals():
                await bot.session.close()
                logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    # Настройка обработки необработанных исключений
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Пропускаем KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    # Запуск бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)