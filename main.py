import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from handlers import admin, user, mailing_constructor
import config
from services.logger import logger
from services.database import db
from services.media_storage import media_storage

async def run_migrations():
    """Запуск миграций при старте"""
    try:
        logger.info("Checking for migrations...")
        
        # Ленивый импорт для избежания циклических зависимостей
        try:
            import migration_universal
            migration_universal.run_universal_migration()
            logger.info("Universal migration completed successfully")
        except ImportError as e:
            logger.error(f"Cannot import migration module: {e}")
            return False
        
        # Дополнительная миграция для полей документов
        try:
            import add_document_fields
            add_document_fields.add_document_fields()
            logger.info("Document fields migration completed successfully")
        except ImportError as e:
            logger.warning(f"Cannot import document fields migration: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Error running migrations: {e}", exc_info=True)
        return False

async def periodic_cleanup():
    """Периодическая очистка старых файлов"""
    import time
    
    while True:
        try:
            # Ждем 24 часа
            await asyncio.sleep(24 * 60 * 60)
            
            logger.info("Running periodic media storage cleanup...")
            
            # Очищаем файлы старше 180 дней
            try:
                stats = media_storage.cleanup_old_files(days_old=180)
                logger.info(f"Cleanup completed: deleted {stats['deleted']} files, kept {stats['kept']}")
            except Exception as e:
                logger.error(f"Error during media storage cleanup: {e}")
            
            # Логируем статистику
            try:
                storage_stats = media_storage.get_storage_stats()
                logger.info(f"Storage stats: {storage_stats['total_files']} files, "
                           f"{storage_stats['total_size_mb']:.2f} MB, "
                           f"oldest: {storage_stats['oldest_file_days']} days")
            except Exception as e:
                logger.error(f"Error getting storage stats: {e}")
            
        except asyncio.CancelledError:
            logger.info("Periodic cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}", exc_info=True)
            await asyncio.sleep(60)  # Пауза перед повторной попыткой

async def setup_bot():
    """Настройка бота и компонентов"""
    try:
        # Инициализация бота с новым синтаксисом для aiogram 3.7.0+
        bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        
        # Устанавливаем бота в хранилище медиа
        media_storage.set_bot(bot)
        
        # Выводим статистику хранилища при старте
        try:
            storage_stats = media_storage.get_storage_stats()
            logger.info(f"Media storage initialized: {storage_stats['total_files']} files, "
                       f"{storage_stats['total_size_mb']:.2f} MB")
        except Exception as e:
            logger.error(f"Error getting initial storage stats: {e}")
        
        dp = Dispatcher(storage=MemoryStorage())
        
        # Регистрация роутеров
        dp.include_router(admin.router)
        dp.include_router(mailing_constructor.router)  
        dp.include_router(user.router)
        
        return bot, dp
        
    except Exception as e:
        logger.error(f"Error setting up bot: {e}", exc_info=True)
        raise

async def main():
    """Основная функция запуска бота"""
    bot = None
    dp = None
    cleanup_task = None
    
    try:
        logger.info("=" * 50)
        logger.info("Bot starting...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Admin IDs: {config.ADMIN_IDS}")
        
        # Запуск миграций
        migration_success = await run_migrations()
        if not migration_success:
            logger.warning("Migrations completed with warnings, continuing...")
        
        # Настройка бота
        bot, dp = await setup_bot()
        
        # Отключаем логирование aiogram, чтобы использовать наше
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
        
        logger.info("Bot started successfully")
        logger.info("=" * 50)
        
        # Запускаем периодическую очистку в фоне
        cleanup_task = asyncio.create_task(periodic_cleanup())
        
        # Запуск бота с обработкой ошибок
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down bot...")
        
        try:
            # Отменяем задачу очистки
            if cleanup_task and not cleanup_task.done():
                cleanup_task.cancel()
                try:
                    await cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Закрываем соединение с базой данных
            if db:
                db.close()
                logger.info("Database connection closed")
            
            # Очищаем старые файлы в хранилище (180+ дней)
            try:
                media_storage.cleanup_old_files(days_old=180)
                logger.info("Media storage cleaned up (180+ days old)")
            except Exception as e:
                logger.error(f"Error cleaning media storage: {e}")
            
            # Выводим финальную статистику
            try:
                final_stats = media_storage.get_storage_stats()
                logger.info(f"Final storage stats: {final_stats['total_files']} files, "
                           f"{final_stats['total_size_mb']:.2f} MB")
            except Exception as e:
                logger.error(f"Error getting final storage stats: {e}")
            
            # Закрываем сессию бота
            if bot:
                try:
                    session = await bot.get_session()
                    await session.close()
                    logger.info("Bot session closed")
                except Exception as e:
                    logger.error(f"Error closing bot session: {e}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def setup_exception_handler():
    """Настройка обработки необработанных исключений"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Пропускаем KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception

if __name__ == "__main__":
    # Настройка обработки необработанных исключений
    setup_exception_handler()
    
    # Запуск бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)