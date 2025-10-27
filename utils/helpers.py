from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.timezone import format_moscow_time

def get_admin_main_keyboard():
    """Главное меню админ-панели"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="📨 Рассылки", callback_data="admin_mailings"))
    keyboard.add(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_stats_keyboard():
    """Меню статистики с кнопкой экспорта и логов"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📈 Общая статистика", callback_data="stats_overview"))
    keyboard.add(InlineKeyboardButton(text="📊 Статистика рассылок", callback_data="stats_mailings"))
    keyboard.add(InlineKeyboardButton(text="👤 Статистика пользователей", callback_data="stats_users"))
    keyboard.add(InlineKeyboardButton(text="📁 Экспорт в Excel", callback_data="export_excel"))
    keyboard.add(InlineKeyboardButton(text="📋 Получить логи", callback_data="get_logs"))
    keyboard.add(InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin_main"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_mailings_keyboard():
    """Меню управления рассылками"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✉️ Создать рассылку", callback_data="create_mailing"))
    keyboard.add(InlineKeyboardButton(text="📤 Активные рассылки", callback_data="mailings_active"))
    keyboard.add(InlineKeyboardButton(text="📝 Черновики", callback_data="mailings_drafts"))
    keyboard.add(InlineKeyboardButton(text="📁 Архив рассылок", callback_data="mailings_archive"))
    keyboard.add(InlineKeyboardButton(text="🚀 Отправить рассылку", callback_data="mailings_send"))
    keyboard.add(InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin_main"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_users_keyboard():
    """Меню управления пользователями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="👥 Список пользователей", callback_data="users_list"))
    keyboard.add(InlineKeyboardButton(text="📅 Активные сегодня", callback_data="users_active_today"))
    keyboard.add(InlineKeyboardButton(text="📊 Аналитика активности", callback_data="users_analytics"))
    keyboard.add(InlineKeyboardButton(text="🔙 Главное меню", callback_data="admin_main"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_mailing_actions_keyboard(mailing_id: int, status: str):
    """Действия для конкретной рассылки"""
    keyboard = InlineKeyboardBuilder()
    
    if status == "draft":
        keyboard.add(InlineKeyboardButton(text="👁️ Просмотр", callback_data=f"view_mailing_{mailing_id}"))
        keyboard.add(InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_mailing_{mailing_id}"))
        keyboard.add(InlineKeyboardButton(text="✅ Активировать", callback_data=f"activate_mailing_{mailing_id}"))
    elif status == "active":
        keyboard.add(InlineKeyboardButton(text="👁️ Просмотр", callback_data=f"view_mailing_{mailing_id}"))
        keyboard.add(InlineKeyboardButton(text="📁 В архив", callback_data=f"archive_mailing_{mailing_id}"))
        keyboard.add(InlineKeyboardButton(text="🚀 Отправить", callback_data=f"send_mailing_{mailing_id}"))
    elif status == "archived":
        keyboard.add(InlineKeyboardButton(text="👁️ Просмотр", callback_data=f"view_mailing_{mailing_id}"))
        keyboard.add(InlineKeyboardButton(text="✅ Активировать", callback_data=f"activate_mailing_{mailing_id}"))
    
    keyboard.add(InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_mailing_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 К списку рассылок", callback_data="admin_mailings"))
    keyboard.adjust(2)
    return keyboard.as_markup()

def get_mailing_type_keyboard():
    """Выбор типа рассылки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📝 Текст", callback_data="mailing_type_text"))
    keyboard.add(InlineKeyboardButton(text="🖼️ Фото + текст", callback_data="mailing_type_photo"))
    keyboard.add(InlineKeyboardButton(text="🎥 Видео + текст", callback_data="mailing_type_video"))
    keyboard.add(InlineKeyboardButton(text="📎 Документ + текст", callback_data="mailing_type_document"))
    keyboard.add(InlineKeyboardButton(text="🎤 Голосовое", callback_data="mailing_type_voice"))
    keyboard.add(InlineKeyboardButton(text="📹 Видео-сообщение", callback_data="mailing_type_video_note"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_mailings"))
    keyboard.adjust(2)
    return keyboard.as_markup()

def get_target_groups_keyboard(mailing_id: int):
    """Выбор целевой группы для рассылки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="👥 Все пользователи", callback_data=f"target_all_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="📅 Активные сегодня", callback_data=f"target_active_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🆕 Новые пользователи (7 дней)", callback_data=f"target_new_week_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🆕 Новые пользователи (30 дней)", callback_data=f"target_new_month_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="mailings_send"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_target_group_name(target_group: str) -> str:
    """Получить читаемое название целевой группы"""
    names = {
        "all": "Все пользователи",
        "active": "Активные сегодня", 
        "new_week": "Новые пользователи (7 дней)",
        "new_month": "Новые пользователи (30 дней)"
    }
    return names.get(target_group, "Неизвестная группа")

def get_back_keyboard(target: str = "admin_main"):
    """Универсальная кнопка назад"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data=target))
    return keyboard.as_markup()

def get_mailing_preview_keyboard(mailing_id: int):
    """Клавиатура для превью рассылки"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🚀 Отправить сейчас", callback_data=f"send_now_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="💾 Сохранить черновик", callback_data=f"save_draft_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="✅ Активировать", callback_data=f"activate_mailing_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 К рассылкам", callback_data="admin_mailings"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_skip_edit_keyboard(mailing_id: int):
    """Клавиатура для пропуска редактирования медиа"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"skip_edit_{mailing_id}"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_mailing_{mailing_id}"))
    keyboard.adjust(1)
    return keyboard.as_markup()

# Функции, которые используют db, будут импортировать его внутри себя
def format_stats_overview():
    """Форматирование общей статистики с московским временем"""
    try:
        from services.database import db  # Локальный импорт для избежания циклических импортов
        
        users_count = db.get_user_count()
        active_today = db.get_active_users_count_today()
        all_mailings = len(db.get_all_mailings())
        active_mailings = len(db.get_mailings_by_status('active'))
        
        return f"""
📊 <b>Общая статистика</b>

👥 <b>Пользователи:</b>
   • Всего: <b>{users_count}</b>
   • Активных сегодня: <b>{active_today}</b>
   • Активность: <b>{(active_today/users_count*100 if users_count > 0 else 0):.1f}%</b>

📨 <b>Рассылки:</b>
   • Всего: <b>{all_mailings}</b>
   • Активных: <b>{active_mailings}</b>

⏱️ <b>Обновлено:</b> {format_moscow_time()}
"""
    except Exception as e:
        return f"❌ Ошибка при загрузке статистики: {e}"

def format_users_stats():
    """Форматирование статистики пользователей"""
    try:
        from services.database import db  # Локальный импорт
        
        users_count = db.get_user_count()
        active_today = db.get_active_users_count_today()
        active_week = db.get_active_users_count_week()
        new_today = db.get_new_users_count(days=1)
        new_week = db.get_new_users_count(days=7)
        
        today_rate = (active_today / users_count * 100) if users_count > 0 else 0
        week_rate = (active_week / users_count * 100) if users_count > 0 else 0
        
        return f"""
👥 <b>Статистика пользователей</b>

📈 <b>Общее:</b>
   • Всего пользователей: <b>{users_count}</b>
   • Активных сегодня: <b>{active_today}</b>
   • Активных за неделю: <b>{active_week}</b>
   • Новых сегодня: <b>{new_today}</b>
   • Новых за неделю: <b>{new_week}</b>

📊 <b>Активность:</b>
   • Сегодня: <b>{today_rate:.1f}%</b>
   • За неделю: <b>{week_rate:.1f}%</b>

⏱️ <b>Обновлено:</b> {format_moscow_time()}
"""
    except Exception as e:
        return f"❌ Ошибка при загрузке статистики пользователей: {e}"

def format_mailings_stats():
    """Форматирование статистики рассылок с московским временем"""
    try:
        from services.database import db  # Локальный импорт
        
        all_mailings = db.get_all_mailings()
        active_mailings = db.get_mailings_by_status('active')
        draft_mailings = db.get_mailings_by_status('draft')
        archived_mailings = db.get_mailings_by_status('archived')
        
        total_sent = 0
        total_delivered = 0
        total_read = 0
        
        for mailing in all_mailings:
            stats = db.get_mailing_stats(mailing['id'])
            total_sent += stats['total_sent']
            total_delivered += stats['delivered']
            total_read += stats['read']
        
        overall_success_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
        overall_read_rate = (total_read / total_sent * 100) if total_sent > 0 else 0
        
        return f"""
📨 <b>Статистика рассылок</b>

📈 <b>Общее:</b>
   • Всего рассылок: <b>{len(all_mailings)}</b>
   • Активных: <b>{len(active_mailings)}</b>
   • Черновиков: <b>{len(draft_mailings)}</b>
   • В архиве: <b>{len(archived_mailings)}</b>

📊 <b>Эффективность:</b>
   • Всего отправлено: <b>{total_sent}</b>
   • Доставлено: <b>{total_delivered}</b>
   • Прочитано: <b>{total_read}</b>
   • Успех доставки: <b>{overall_success_rate:.1f}%</b>
   • Процент прочтения: <b>{overall_read_rate:.1f}%</b>

⏱️ <b>Обновлено:</b> {format_moscow_time()}
"""
    except Exception as e:
        return f"❌ Ошибка при загрузке статистики рассылок: {e}"

def get_logs_keyboard():
    """Клавиатура для выбора логов"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📋 Текущий месяц", callback_data="logs_current"))
    keyboard.add(InlineKeyboardButton(text="📋 Предыдущий месяц", callback_data="logs_previous"))
    keyboard.add(InlineKeyboardButton(text="📋 Все логи", callback_data="logs_all"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_stats"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def format_mailing_preview(mailing):
    """Форматирование превью рассылки с московским временем"""
    try:
        from services.database import db
        
        type_emojis = {
            'text': '📝',
            'photo': '🖼️',
            'video': '🎥',
            'document': '📎',
            'voice': '🎤',
            'video_note': '📹'
        }
        
        status_texts = {
            'draft': '📝 Черновик',
            'active': '✅ Активна',
            'archived': '📁 В архиве'
        }
        
        stats = db.get_mailing_stats(mailing['id'])
        
        message_text = mailing['message_text']
        preview_text = message_text[:200] + '...' if len(message_text) > 200 else message_text
        
        # ИСПРАВЛЕНИЕ: проверяем на None перед вызовом strftime
        created_at = format_moscow_time(mailing['created_at']) if mailing.get('created_at') else 'неизвестно'
        updated_at = format_moscow_time(mailing['updated_at']) if mailing.get('updated_at') else 'неизвестно'
        
        return f"""
{type_emojis.get(mailing['message_type'], '📝')} <b>Просмотр рассылки</b>

📋 <b>Название:</b> {mailing['title']}
📄 <b>Текст:</b> {preview_text}
🎬 <b>Тип:</b> {mailing['message_type']}
📊 <b>Статус:</b> {status_texts.get(mailing['status'], mailing['status'])}
📈 <b>Статистика:</b> Отправлено: {stats['total_sent']}, Успешно: {stats['delivered']}
⏰ <b>Создана:</b> {created_at}
🔄 <b>Обновлена:</b> {updated_at}
"""
    except Exception as e:
        return f"❌ Ошибка при форматировании превью рассылки: {e}"