"""
Модуль логирования
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from typing import Optional

try:
    from utils.constants import LOG_DIR
except ImportError:
    LOG_DIR = "logs"

class BotLogger:
    def __init__(self, log_dir: str = LOG_DIR):
        self.log_dir = log_dir
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка системы логирования"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Формат логов
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Основной логгер
        self.logger = logging.getLogger('telegram_bot')
        self.logger.setLevel(logging.INFO)
        
        # Очистка существующих обработчиков
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Файловый обработчик
        log_file = os.path.join(self.log_dir, f"bot_{datetime.now().strftime('%Y%m')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(log_format, datefmt=date_format)
        console_handler.setFormatter(console_formatter)
        
        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Отключаем логирование для внешних библиотек
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
    
    def info(self, message: str, user_id: Optional[int] = None):
        """Логирование информационного сообщения"""
        if user_id:
            message = f"[User:{user_id}] {message}"
        self.logger.info(message)
    
    def error(self, message: str, user_id: Optional[int] = None, exc_info: bool = False):
        """Логирование ошибки"""
        if user_id:
            message = f"[User:{user_id}] {message}"
        self.logger.error(message, exc_info=exc_info)
    
    def warning(self, message: str, user_id: Optional[int] = None):
        """Логирование предупреждения"""
        if user_id:
            message = f"[User:{user_id}] {message}"
        self.logger.warning(message)
    
    def debug(self, message: str, user_id: Optional[int] = None):
        """Логирование отладочной информации"""
        if user_id:
            message = f"[User:{user_id}] {message}"
        self.logger.debug(message)
    
    def log_mailing_start(self, mailing_id: int, mailing_title: str, target_group: str, total_users: int):
        """Логирование начала рассылки"""
        self.info(f"📨 Starting mailing: ID={mailing_id}, Title='{mailing_title}', "
                 f"Target={target_group}, Users={total_users}")
    
    def log_mailing_progress(self, mailing_id: int, current: int, total: int, success_count: int):
        """Логирование прогресса рассылки"""
        progress = (current / total * 100) if total > 0 else 0
        self.info(f"📨 Mailing {mailing_id} progress: {current}/{total} ({progress:.1f}%), "
                 f"Success: {success_count}")
    
    def log_mailing_complete(self, mailing_id: int, success_count: int, total: int, errors: int):
        """Логирование завершения рассылки"""
        success_rate = (success_count / total * 100) if total > 0 else 0
        self.info(f"📨 Mailing {mailing_id} completed: {success_count}/{total} ({success_rate:.1f}%), "
                 f"Errors: {errors}")
    
    def log_user_activity(self, user_id: int, action: str):
        """Логирование активности пользователя"""
        self.info(f"👤 User activity: {action}", user_id=user_id)
    
    def log_admin_action(self, admin_id: int, action: str):
        """Логирование действий администратора"""
        self.info(f"👨‍💻 Admin action: {action}", user_id=admin_id)
    
    def get_log_file_path(self, month: Optional[str] = None) -> str:
        """Получить путь к файлу лога"""
        if month is None:
            month = datetime.now().strftime('%Y%m')
        return os.path.join(self.log_dir, f"bot_{month}.log")
    
    def get_available_logs(self) -> list:
        """Получить список доступных лог-файлов"""
        if not os.path.exists(self.log_dir):
            return []
        
        log_files = []
        for file in os.listdir(self.log_dir):
            if file.startswith('bot_') and file.endswith('.log'):
                # Извлекаем дату из имени файла
                date_str = file[4:-4]  # Убираем 'bot_' и '.log'
                try:
                    date = datetime.strptime(date_str, '%Y%m')
                    log_files.append({
                        'filename': file,
                        'date': date,
                        'path': os.path.join(self.log_dir, file)
                    })
                except ValueError:
                    continue
        
        # Сортируем по дате (новые сначала)
        log_files.sort(key=lambda x: x['date'], reverse=True)
        return log_files

# Создаем глобальный экземпляр логгера
logger = BotLogger()