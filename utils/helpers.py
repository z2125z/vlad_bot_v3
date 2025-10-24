from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📊 Статистика пользователей", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton(text="📨 Рассылки", callback_data="admin_mailings"))
    keyboard.add(InlineKeyboardButton(text="✉️ Создать рассылку", callback_data="create_mailing"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_mailings_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="📈 Статистика рассылок", callback_data="mailings_stats"))
    keyboard.add(InlineKeyboardButton(text="📋 История рассылок", callback_data="mailings_history"))
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main"))
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_back_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_main"))
    return keyboard.as_markup()

def format_user_stats(users_count, active_today):
    return f"""
📊 <b>Статистика пользователей</b>

👥 Всего пользователей: <b>{users_count}</b>
📅 Активных за сегодня: <b>{active_today}</b>
    """

def format_mailing_stats(stats_data):
    stats = stats_data
    return f"""
📨 <b>Статистика рассылки</b>

📝 Название: <b>{stats['mailing'].title}</b>
📤 Отправлено: <b>{stats['total_sent']}</b>
✅ Доставлено: <b>{stats['delivered']}</b>
👀 Прочитано: <b>{stats['read']}</b>
📊 Эффективность: <b>{(stats['delivered']/stats['total_sent']*100 if stats['total_sent'] > 0 else 0):.1f}%</b>
    """