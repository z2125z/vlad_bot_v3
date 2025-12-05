"""
Константы бота
"""

# Типы сообщений
MESSAGE_TYPES = {
    "text": "📝 Текст",
    "photo": "🖼️ Фото + текст", 
    "video": "🎥 Видео + текст",
    "document": "📎 Документ + текст",
    "voice": "🎤 Голосовое",
    "video_note": "📹 Видео-сообщение"
}

# Типы медиа для Telegram
MEDIA_CONTENT_TYPES = {
    "photo": "photo",
    "video": "video", 
    "document": "document",
    "voice": "voice",
    "video_note": "video_note"
}

# Статусы рассылок
MAILING_STATUSES = {
    "draft": "📝 Черновик",
    "active": "✅ Активна", 
    "archived": "📁 В архиве",
    "deleted": "🗑️ Удалена"
}

# Целевые группы рассылок
TARGET_GROUPS = {
    "all": "👥 Все пользователи",
    "active": "📅 Активные сегодня",
    "new_week": "🆕 Новые пользователи (7 дней)",
    "new_month": "🆕 Новые пользователи (30 дней)",
    "trigger": "🔤 По кодовому слову"
}

# Эмодзи для типов рассылок
TYPE_EMOJIS = {
    'text': '📝',
    'photo': '🖼️',
    'video': '🎥',
    'document': '📎',
    'voice': '🎤',
    'video_note': '📹'
}

# Лимиты
MAX_TITLE_LENGTH = 200
MAX_TRIGGER_WORD_LENGTH = 50
MAX_BUTTONS_PER_ROW = 3

# Форматы времени
TIME_FORMAT = '%d.%m.%Y %H:%M'
DATE_FORMAT = '%d.%m.%Y'
FILENAME_TIME_FORMAT = '%Y%m%d_%H%M%S'

# Настройки бота
DEFAULT_BATCH_SIZE = 100
MAX_PARALLEL_SEND = 20
SEND_DELAY = 0.05  # 20 сообщений в секунду

# Настройки хранилища
STORAGE_CLEANUP_DAYS = 180
STORAGE_FORCE_CLEANUP_DAYS = 30

# Пути
LOG_DIR = "logs"
MEDIA_STORAGE_DIR = "media_storage"
EXPORT_DIR = "exports"