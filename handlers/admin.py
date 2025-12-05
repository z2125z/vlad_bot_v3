from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from utils.helpers import (
    get_admin_main_keyboard,
    get_stats_keyboard,
    get_mailings_keyboard,
    get_users_keyboard,
    get_target_groups_keyboard,
    get_back_keyboard,
    get_logs_keyboard,
    get_pagination_keyboard,
    get_mailing_actions_keyboard
)
import config
import os
from services.logger import logger
from datetime import datetime, timedelta
import asyncio
import math

router = Router()

def is_admin(user_id: int):
    return user_id in config.ADMIN_IDS

# Главная команда админа
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(
        "👨‍💻 <b>Админ панель</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    logger.log_admin_action(message.from_user.id, "opened admin panel")

# 📊 РАЗДЕЛ СТАТИСТИКИ
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "📊 <b>Статистика</b>\n\n"
        "Выберите тип статистики для просмотра:",
        reply_markup=get_stats_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Общая статистика
@router.callback_query(F.data == "stats_overview")
async def stats_overview(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from utils.helpers import format_stats_overview
        stats_text = format_stats_overview()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading stats overview: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

# Статистика пользователей
@router.callback_query(F.data == "stats_users")
async def stats_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from utils.helpers import format_users_stats
        stats_text = format_users_stats()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading user stats: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики пользователей: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

# Статистика рассылок
@router.callback_query(F.data == "stats_mailings")
async def stats_mailings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from utils.helpers import format_mailings_stats
        stats_text = format_mailings_stats()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading mailing stats: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики рассылок: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

# 📨 РАЗДЕЛ РАССЫЛОК
@router.callback_query(F.data == "admin_mailings")
async def admin_mailings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "📨 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_mailings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Активные рассылки с пагинацией
@router.callback_query(F.data.startswith("mailings_active_"))
async def mailings_active(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        # Получаем номер страницы из callback_data
        page_str = callback.data.replace("mailings_active_", "")
        try:
            page = int(page_str)
        except ValueError:
            page = 1
            
        # Получаем все активные рассылки
        mailings = db.get_mailings_by_status('active')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет активных рассылок",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        # Настройки пагинации
        items_per_page = 10
        total_items = len(mailings)
        total_pages = max(1, math.ceil(total_items / items_per_page))
        page = max(1, min(page, total_pages))
        
        # Вычисляем диапазон для текущей страницы
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_mailings = mailings[start_idx:end_idx]
        
        text = f"✅ <b>Активные рассылки (страница {page}/{total_pages}):</b>\n\n"
        
        for mailing in current_mailings:
            stats = db.get_mailing_stats(mailing['id'])
            created_at = mailing['created_at'].strftime('%d.%m.%Y') if mailing['created_at'] else 'неизвестно'
            
            # Добавляем информацию о кодовом слове, если есть
            trigger_word_info = ""
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                trigger_word_info = f" 🔤{mailing['trigger_word']}"
            
            text += f"📨 {mailing['title']}{trigger_word_info}\n"
            text += f"   📊 Отправлено: {stats['delivered']}/{stats['total_sent']}\n"
            text += f"   🕐 Создана: {created_at}\n"
            text += f"   [ID: {mailing['id']}]\n\n"
        
        # Создаем клавиатуру с пагинацией
        keyboard = InlineKeyboardBuilder()
        
        for mailing in current_mailings:
            button_text = f"📝 {mailing['title'][:20]}..."
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                button_text = f"🔤 {mailing['trigger_word']}"
            
            keyboard.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_mailing_{mailing['id']}"
            ))
        
        keyboard.adjust(1)
        
        # Добавляем пагинацию
        pagination_keyboard = get_pagination_keyboard(page, total_pages, "mailings_active")
        
        # Объединяем клавиатуры
        combined_keyboard = InlineKeyboardBuilder()
        for button in keyboard.export():
            combined_keyboard.add(button)
        
        for button in pagination_keyboard.inline_keyboard[0]:
            combined_keyboard.add(InlineKeyboardButton(
                text=button.text,
                callback_data=button.callback_data
            ))
        
        combined_keyboard.adjust(1, 3)
        
        await callback.message.edit_text(
            text,
            reply_markup=combined_keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading active mailings: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке активных рассылок: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Черновики с пагинацией
@router.callback_query(F.data.startswith("mailings_drafts_"))
async def mailings_drafts(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        # Получаем номер страницы из callback_data
        page_str = callback.data.replace("mailings_drafts_", "")
        try:
            page = int(page_str)
        except ValueError:
            page = 1
            
        mailings = db.get_mailings_by_status('draft')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет черновиков рассылок",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        # Настройки пагинации
        items_per_page = 10
        total_items = len(mailings)
        total_pages = max(1, math.ceil(total_items / items_per_page))
        page = max(1, min(page, total_pages))
        
        # Вычисляем диапазон для текущей страницы
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_mailings = mailings[start_idx:end_idx]
        
        text = f"📝 <b>Черновики рассылок (страница {page}/{total_pages}):</b>\n\n"
        
        for mailing in current_mailings:
            created_at = mailing['created_at'].strftime('%d.%m.%Y') if mailing['created_at'] else 'неизвестно'
            
            # Добавляем информация о кодовом слове, если есть
            trigger_word_info = ""
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                trigger_word_info = f" 🔤{mailing['trigger_word']}"
            
            text += f"📄 {mailing['title']}{trigger_word_info}\n"
            text += f"   🕐 Создан: {created_at}\n"
            text += f"   [ID: {mailing['id']}]\n\n"
        
        # Создаем клавиатуру с пагинацией
        keyboard = InlineKeyboardBuilder()
        
        for mailing in current_mailings:
            button_text = f"📝 {mailing['title'][:20]}..."
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                button_text = f"🔤 {mailing['trigger_word']}"
            
            keyboard.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_mailing_{mailing['id']}"
            ))
        
        keyboard.adjust(1)
        
        # Добавляем пагинацию
        pagination_keyboard = get_pagination_keyboard(page, total_pages, "mailings_drafts")
        
        # Объединяем клавиатуры
        combined_keyboard = InlineKeyboardBuilder()
        for button in keyboard.export():
            combined_keyboard.add(button)
        
        for button in pagination_keyboard.inline_keyboard[0]:
            combined_keyboard.add(InlineKeyboardButton(
                text=button.text,
                callback_data=button.callback_data
            ))
        
        combined_keyboard.adjust(1, 3)
        
        await callback.message.edit_text(
            text,
            reply_markup=combined_keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading draft mailings: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке черновиков: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Архив рассылок с пагинацией
@router.callback_query(F.data.startswith("mailings_archive_"))
async def mailings_archive(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        # Получаем номер страницы из callback_data
        page_str = callback.data.replace("mailings_archive_", "")
        try:
            page = int(page_str)
        except ValueError:
            page = 1
            
        mailings = db.get_mailings_by_status('archived')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет рассылок в архиве",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        # Настройки пагинации
        items_per_page = 10
        total_items = len(mailings)
        total_pages = max(1, math.ceil(total_items / items_per_page))
        page = max(1, min(page, total_pages))
        
        # Вычисляем диапазон для текущей страницы
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_mailings = mailings[start_idx:end_idx]
        
        text = f"📁 <b>Архив рассылок (страница {page}/{total_pages}):</b>\n\n"
        
        for mailing in current_mailings:
            stats = db.get_mailing_stats(mailing['id'])
            created_at = mailing['created_at'].strftime('%d.%m.%Y') if mailing['created_at'] else 'неизвестно'
            
            # Добавляем информация о кодовом слове, если есть
            trigger_word_info = ""
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                trigger_word_info = f" 🔤{mailing['trigger_word']}"
            
            text += f"📨 {mailing['title']}{trigger_word_info}\n"
            text += f"   📊 Отправлено: {stats['delivered']}/{stats['total_sent']}\n"
            text += f"   🕐 Создана: {created_at}\n"
            text += f"   [ID: {mailing['id']}]\n\n"
        
        # Создаем клавиатуру с пагинацией
        keyboard = InlineKeyboardBuilder()
        
        for mailing in current_mailings:
            button_text = f"📝 {mailing['title'][:20]}..."
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                button_text = f"🔤 {mailing['trigger_word']}"
            
            keyboard.add(InlineKeyboardButton(
                text=button_text,
                callback_data=f"view_mailing_{mailing['id']}"
            ))
        
        keyboard.adjust(1)
        
        # Добавляем пагинацию
        pagination_keyboard = get_pagination_keyboard(page, total_pages, "mailings_archive")
        
        # Объединяем клавиатуры
        combined_keyboard = InlineKeyboardBuilder()
        for button in keyboard.export():
            combined_keyboard.add(button)
        
        for button in pagination_keyboard.inline_keyboard[0]:
            combined_keyboard.add(InlineKeyboardButton(
                text=button.text,
                callback_data=button.callback_data
            ))
        
        combined_keyboard.adjust(1, 3)
        
        await callback.message.edit_text(
            text,
            reply_markup=combined_keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading archived mailings: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке архива: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Меню отправки рассылки
@router.callback_query(F.data == "mailings_send")
async def mailings_send(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        active_mailings = db.get_mailings_by_status('active')
        
        if not active_mailings:
            await callback.message.edit_text(
                "❌ Нет активных рассылок для отправки",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        text = "🚀 <b>Отправка рассылки</b>\n\nВыберите рассылку:\n\n"
        keyboard = InlineKeyboardBuilder()
        
        for mailing in active_mailings:
            # Добавляем иконку кодового слова к названию
            mailing_title = mailing['title']
            if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
                mailing_title = f"🔤 {mailing['trigger_word']} ({mailing['title'][:15]}...)"
            
            keyboard.add(InlineKeyboardButton(
                text=f"📨 {mailing_title}",
                callback_data=f"select_mailing_{mailing['id']}"
            ))
        
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_mailings"))
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading mailings for sending: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке рассылок: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Выбор целевой группы
@router.callback_query(F.data.startswith("select_mailing_"))
async def select_mailing_target(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        mailing_id = int(callback.data.replace("select_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        users_count = db.get_user_count()
        active_today = db.get_active_users_count_today()
        new_week = db.get_new_users_count_week()
        new_month = db.get_new_users_count_month()
        
        # Добавляем информация о кодовом слове
        trigger_info = ""
        if mailing.get('is_trigger_mailing') and mailing.get('trigger_word'):
            stats = db.get_mailing_stats(mailing_id)
            trigger_info = f"\n🔤 <b>Кодовое слово:</b> {mailing['trigger_word']}\n📊 <b>Отправок:</b> {stats['delivered']}"
        
        await callback.message.edit_text(
            f"🎯 <b>Выбор целевой группы</b>\n\n"
            f"📨 <b>Рассылка:</b> {mailing['title']}{trigger_info}\n\n"
            f"👥 <b>Доступные группы:</b>\n"
            f"   • Все пользователи: {users_count} чел.\n"
            f"   • Активные сегодня: {active_today} чел.\n"
            f"   • Новые пользователи (7 дней): {new_week} чел.\n"
            f"   • Новые пользователи (30 дней): {new_month} чел.",
            reply_markup=get_target_groups_keyboard(mailing_id),
            parse_mode="HTML"
        )
        logger.log_admin_action(callback.from_user.id, f"selected mailing {mailing_id} for sending")
    except Exception as e:
        logger.error(f"Error selecting mailing: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при выборе рассылки: {str(e)}",
            reply_markup=get_back_keyboard("mailings_send")
        )
    await callback.answer()

# Запуск рассылки - ВАЖНОЕ ИСПРАВЛЕНИЕ
@router.callback_query(F.data.startswith("target:"))
async def start_mailing_broadcast(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        from utils.helpers import get_target_group_name
        
        # Правильный разбор callback_data
        data_parts = callback.data.split(":")
        if len(data_parts) != 3:
            await callback.answer("❌ Ошибка в данных")
            return
            
        target_group = data_parts[1]  # all, active, new_week, new_month
        mailing_id = int(data_parts[2])
        
        mailing = db.get_mailing(mailing_id)
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        from services.mailing import MailingService
        mailing_service = MailingService(bot)
        
        await callback.message.edit_text("🔄 Начинаю рассылку...")
        
        success, success_count, total_count = await mailing_service.broadcast_mailing(
            mailing_id=mailing_id,
            target_group=target_group
        )
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📋 <b>Рассылка:</b> {mailing['title']}\n"
                f"🎯 <b>Целевая группа:</b> {get_target_group_name(target_group)}\n"
                f"📤 <b>Отправлено:</b> {success_count}/{total_count} сообщений\n"
                f"📊 <b>Успешных:</b> {(success_count/total_count*100 if total_count > 0 else 0):.1f}%",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            logger.log_admin_action(callback.from_user.id, 
                                  f"completed mailing {mailing_id} to {target_group}: {success_count}/{total_count}")
        else:
            await callback.message.edit_text(
                "❌ Ошибка при рассылке",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            logger.error(f"Failed to send mailing {mailing_id} to {target_group}")
    except Exception as e:
        logger.error(f"Error starting mailing broadcast: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при запуске рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# 👥 РАЗДЕЛ ПОЛЬЗОВАТЕЛЕЙ
@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_users_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Список пользователей
@router.callback_query(F.data == "users_list")
async def users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        users = db.get_all_users(limit=50)
        
        if not users:
            await callback.message.edit_text(
                "❌ Нет пользователей",
                reply_markup=get_back_keyboard("admin_users")
            )
            return
        
        text = "👥 <b>Последние пользователи:</b>\n\n"
        for user in users[:10]:
            status = "🟢" if user.is_active else "🔴"
            username = f"@{user.username}" if user.username else "без username"
            text += f"{status} {user.full_name or 'Без имени'}\n"
            text += f"   👤 {username}\n"
            text += f"   🆔 ID: {user.user_id}\n"
            text += f"   🕐 Регистрация: {user.joined_at.strftime('%d.%m.%Y')}\n\n"
        
        if len(users) > 10:
            text += f"... и еще {len(users) - 10} пользователей"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_users"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading users list: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке пользователей: {str(e)}",
            reply_markup=get_back_keyboard("admin_users")
        )
    await callback.answer()

# Активные сегодня
@router.callback_query(F.data == "users_active_today")
async def users_active_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        users = db.get_active_users_today()
        
        if not users:
            await callback.message.edit_text(
                "❌ Нет активных пользователей за сегодня",
                reply_markup=get_back_keyboard("admin_users")
            )
            return
        
        text = "📅 <b>Активные пользователи сегодня:</b>\n\n"
        for user in users[:10]:
            text += f"🟢 {user.full_name or 'Без имени'}\n"
            text += f"   👤 @{user.username or 'без username'}\n"
            text += f"   ⏰ Активность: {user.last_activity.strftime('%H:%M')}\n\n"
        
        if len(users) > 10:
            text += f"... и еще {len(users) - 10} пользователей"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_users"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading active users: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке активных пользователей: {str(e)}",
            reply_markup=get_back_keyboard("admin_users")
        )
    await callback.answer()

# Аналитика активности
@router.callback_query(F.data == "users_analytics")
async def users_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        total_users = db.get_user_count()
        active_today = db.get_active_users_count_today()
        active_week = db.get_active_users_count_week()
        new_today = db.get_new_users_count(days=1)
        new_week = db.get_new_users_count_week()
        new_month = db.get_new_users_count_month()
        
        today_rate = (active_today / total_users * 100) if total_users > 0 else 0
        week_rate = (active_week / total_users * 100) if total_users > 0 else 0
        
        text = f"""
📊 <b>Аналитика активности пользователей</b>

👥 <b>Общая статистика:</b>
   • Всего пользователей: {total_users}
   • Активных сегодня: {active_today}
   • Активных за неделю: {active_week}
   • Новых сегодня: {new_today}
   • Новых за неделю: {new_week}
   • Новых за месяц: {new_month}

📈 <b>Процент активности:</b>
   • За сегодня: {today_rate:.1f}%
   • За неделю: {week_rate:.1f}%

📅 <b>Тенденции:</b>
   • Рост за неделю: +{new_week} пользователей
   • Рост за месяц: +{new_month} пользователей
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_users"),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading user analytics: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке аналитики: {str(e)}",
            reply_markup=get_back_keyboard("admin_users")
        )
    await callback.answer()

# Главное меню
@router.callback_query(F.data == "admin_main")
async def admin_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👨‍💻 <b>Админ панель</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Экспорт в Excel
@router.callback_query(F.data == "export_excel")
async def export_to_excel(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text("📊 Генерируем Excel отчет... Это может занять несколько секунд.")
        
        from services.excel_export import ExcelExporter
        exporter = ExcelExporter()
        filepath = exporter.generate_full_report()
        
        if not filepath:
            await callback.message.edit_text(
                "❌ Ошибка при генерации отчета. Проверьте логи для подробностей.",
                reply_markup=get_back_keyboard("admin_stats")
            )
            return
        
        # Отправляем файл
        file = FSInputFile(filepath)
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=file,
            caption="📊 <b>Полный отчет бота</b>\n\n"
                   "Файл содержит следующие листы:\n"
                   "• Пользователи - все данные пользователей\n"
                   "• Рассылки - информация о всех рассылках\n"
                   "• Статистика рассылок - эффективность рассылок\n"
                   "• Общая статистика - сводные данные\n"
                   "• Активность пользователей - анализ активности",
            parse_mode="HTML"
        )
        
        # Удаляем временный файл после успешной отправки
        try:
            # Ждем немного перед удалением
            await asyncio.sleep(5)
            os.remove(filepath)
            logger.debug(f"Removed temporary export file: {filepath}")
        except Exception as e:
            logger.warning(f"Could not remove temp file {filepath}: {e}")
            
        # Очищаем старые экспорты
        exporter.cleanup_old_exports()
        
        await callback.message.edit_text(
            "✅ <b>Excel отчет успешно сгенерирован и отправлен!</b>",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("admin_stats")
        )
        
        logger.log_admin_action(callback.from_user.id, "exported Excel report")
        
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при генерации отчета: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

# Просмотр конкретной рассылки
@router.callback_query(F.data.startswith("view_mailing_"))
async def view_mailing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        from utils.helpers import format_mailing_preview, get_mailing_actions_keyboard
        
        mailing_id = int(callback.data.replace("view_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        preview_text = format_mailing_preview(mailing)
        await callback.message.edit_text(
            preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_actions_keyboard(mailing_id, mailing['status'])
        )
    except Exception as e:
        logger.error(f"Error viewing mailing {mailing_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Архивирование рассылки
@router.callback_query(F.data.startswith("archive_mailing_"))
async def archive_mailing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        mailing_id = int(callback.data.replace("archive_mailing_", ""))
        db.change_mailing_status(mailing_id, "archived")
        
        await callback.answer("✅ Рассылка перемещена в архив")
        await callback.message.answer(
            "✅ Рассылка перемещена в архив",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"archived mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error archiving mailing {mailing_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при архивировании рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Активация рассылки
@router.callback_query(F.data.startswith("activate_mailing_"))
async def activate_mailing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        mailing_id = int(callback.data.replace("activate_mailing_", ""))
        db.change_mailing_status(mailing_id, "active")
        
        await callback.answer("✅ Рассылка активирована")
        await callback.message.answer(
            "✅ Рассылка активирована и готова к отправке",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"activated mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error activating mailing {mailing_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при активации рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Удаление рассылки
@router.callback_query(F.data.startswith("delete_mailing_"))
async def delete_mailing(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        mailing_id = int(callback.data.replace("delete_mailing_", ""))
        db.change_mailing_status(mailing_id, "deleted")
        
        await callback.answer("✅ Рассылка удалена")
        await callback.message.answer(
            "✅ Рассылка удалена",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"deleted mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error deleting mailing {mailing_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при удалении рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Обработка кнопки отправки конкретной рассылки
@router.callback_query(F.data.startswith("send_mailing_"))
async def send_specific_mailing(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.database import db
        
        mailing_id = int(callback.data.replace("send_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        await callback.message.edit_text(
            f"🎯 <b>Выбор целевой группы для рассылки</b>\n\n"
            f"📨 Рассылка: <b>{mailing['title']}</b>\n\n"
            "Выберите целевую группу:",
            reply_markup=get_target_groups_keyboard(mailing_id),
            parse_mode="HTML"
        )
        logger.log_admin_action(callback.from_user.id, f"initiated sending for mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error initiating mailing send {mailing_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при выборе рассылки: {str(e)}",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Получение логов
@router.callback_query(F.data == "get_logs")
async def get_logs_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text(
            "📋 <b>Получение логов</b>\n\n"
            "Выберите период для скачивания логов:",
            reply_markup=get_logs_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in get_logs_menu: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке меню логов: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

@router.callback_query(F.data == "logs_current")
async def send_current_month_logs(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text("📋 Подготавливаю логи за текущий месяц...")
        
        current_month = datetime.now().strftime('%Y%m')
        log_file_path = logger.get_log_file_path(current_month)
        
        if not os.path.exists(log_file_path):
            await callback.message.edit_text(
                "❌ Логи за текущий месяц не найдены",
                reply_markup=get_back_keyboard("get_logs")
            )
            return
        
        # Отправляем файл лога
        file = FSInputFile(log_file_path)
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=file,
            caption=f"📋 <b>Логи бота за текущий месяц</b>\n\n"
                   f"Файл: <code>bot_{current_month}.log</code>\n"
                   f"Размер: {os.path.getsize(log_file_path) / 1024:.1f} КБ",
            parse_mode="HTML"
        )
        
        await callback.message.edit_text(
            "✅ Логи за текущий месяц отправлены!",
            reply_markup=get_back_keyboard("admin_stats")
        )
        
        logger.log_admin_action(callback.from_user.id, "downloaded current month logs")
        
    except Exception as e:
        logger.error(f"Error sending current month logs: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при отправке логов: {str(e)}",
            reply_markup=get_back_keyboard("get_logs")
        )
    await callback.answer()

@router.callback_query(F.data == "logs_previous")
async def send_previous_month_logs(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text("📋 Подготавливаю логи за предыдущий месяц...")
        
        # Получаем предыдущий месяц
        first_day = datetime.now().replace(day=1)
        previous_month = (first_day - timedelta(days=1)).strftime('%Y%m')
        log_file_path = logger.get_log_file_path(previous_month)
        
        if not os.path.exists(log_file_path):
            await callback.message.edit_text(
                "❌ Логи за предыдущий месяц не найдены",
                reply_markup=get_back_keyboard("get_logs")
            )
            return
        
        # Отправляем файл лога
        file = FSInputFile(log_file_path)
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=file,
            caption=f"📋 <b>Логи бота за предыдущий месяц</b>\n\n"
                   f"Файл: <code>bot_{previous_month}.log</code>\n"
                   f"Размер: {os.path.getsize(log_file_path) / 1024:.1f} КБ",
            parse_mode="HTML"
        )
        
        await callback.message.edit_text(
            "✅ Логи за предыдущий месяц отправлены!",
            reply_markup=get_back_keyboard("admin_stats")
        )
        
        logger.log_admin_action(callback.from_user.id, "downloaded previous month logs")
        
    except Exception as e:
        logger.error(f"Error sending previous month logs: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при отправке логов: {str(e)}",
            reply_markup=get_back_keyboard("get_logs")
        )
    await callback.answer()

@router.callback_query(F.data == "storage_stats")
async def storage_stats(callback: CallbackQuery):
    """Статистика хранилища медиафайлов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.media_storage import media_storage
        
        stats = media_storage.get_storage_stats()
        
        # Форматируем информация о типах файлов
        file_types_info = ""
        for file_type, count in stats.get('file_types', {}).items():
            file_types_info += f"   • {file_type}: {count} файлов\n"
        
        text = f"""
📦 <b>Статистика хранилища медиафайлов</b>

📁 <b>Общая информация:</b>
   • Всего файлов: {stats['total_files']}
   • Размер хранилища: {stats['total_size_mb']:.2f} MB
   • Записей в метаданных: {stats['metadata_entries']}
   • Возраст самого старого файла: {stats['oldest_file_days']} дней

📊 <b>Файлы по типам:</b>
{file_types_info}

📍 <b>Путь к хранилищу:</b>
<code>{stats['storage_path']}</code>

⚙️ <b>Настройки очистки:</b>
• Автоматически удаляются файлы старше 180 дней
• Очистка выполняется каждые 24 часа
        """
        
        # Создаем клавиатуру с кнопками управления
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(
            text="🧹 Очистить файлы старше 180 дней", 
            callback_data="storage_cleanup_180"
        ))
        keyboard.add(InlineKeyboardButton(
            text="⚠️ Очистить неиспользуемые 30+ дней", 
            callback_data="storage_cleanup_30"
        ))
        keyboard.add(InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="storage_stats"))
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_stats"))
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error loading storage stats: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики хранилища: {str(e)}",
            reply_markup=get_back_keyboard("admin_stats")
        )
    await callback.answer()

@router.callback_query(F.data == "storage_cleanup_180")
async def storage_cleanup_180(callback: CallbackQuery):
    """Очистка файлов старше 180 дней"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.media_storage import media_storage
        
        await callback.message.edit_text("🧹 Очищаю файлы старше 180 дней...")
        
        stats = media_storage.cleanup_old_files(days_old=180)
        
        text = f"""
✅ <b>Очистка завершена!</b>

📊 <b>Результаты:</b>
   • Удалено файлов: {stats['deleted']}
   • Оставлено файлов: {stats['kept']}
   • Всего записей: {stats['total_metadata']}

⚙️ <b>Критерии очистки:</b>
• Удалены файлы, которые не использовались 180+ дней
• Метаданные обновлены
        """
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📊 Обновить статистику", callback_data="storage_stats"))
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_stats"))
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
        logger.log_admin_action(callback.from_user.id, f"cleaned storage (180 days): deleted {stats['deleted']} files")
        
    except Exception as e:
        logger.error(f"Error cleaning storage: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при очистке хранилища: {str(e)}",
            reply_markup=get_back_keyboard("storage_stats")
        )
    await callback.answer()

@router.callback_query(F.data == "storage_cleanup_30")
async def storage_cleanup_30(callback: CallbackQuery):
    """Очистка неиспользуемых файлов (30+ дней)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        from services.media_storage import media_storage
        
        await callback.message.edit_text("⚠️ Очищаю файлы, неиспользуемые 30+ дней...")
        
        deleted_count = media_storage.force_cleanup_all_unused(days_unused=30)
        
        text = f"""
⚠️ <b>Принудительная очистка завершена!</b>

📊 <b>Результаты:</b>
   • Удалено файлов: {deleted_count}

❗ <b>Внимание:</b>
• Удалены ВСЕ файлы, которые не использовались 30+ дней
• Включая файлы, которые могут понадобиться в будущем
• Используйте осторожно!
        """
        
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="📊 Обновить статистику", callback_data="storage_stats"))
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_stats"))
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
        logger.log_admin_action(callback.from_user.id, f"force cleaned storage (30 days): deleted {deleted_count} files")
        
    except Exception as e:
        logger.error(f"Error force cleaning storage: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при принудительной очистке хранилища: {str(e)}",
            reply_markup=get_back_keyboard("storage_stats")
        )
    await callback.answer()

@router.callback_query(F.data == "logs_all")
async def send_all_logs(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text("📋 Подготавливаю все доступные логи...")
        
        available_logs = logger.get_available_logs()
        
        if not available_logs:
            await callback.message.edit_text(
                "❌ Логи не найдены",
                reply_markup=get_back_keyboard("get_logs")
            )
            return
        
        sent_count = 0
        for log_info in available_logs:
            try:
                file = FSInputFile(log_info['path'])
                await bot.send_document(
                    chat_id=callback.from_user.id,
                    document=file,
                    caption=f"📋 <b>Лог бота</b>\n\n"
                           f"Период: {log_info['date'].strftime('%B %Y')}\n"
                           f"Файл: <code>{log_info['filename']}</code>\n"
                           f"Размер: {os.path.getsize(log_info['path']) / 1024:.1f} КБ",
                    parse_mode="HTML"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending log file {log_info['filename']}: {e}")
        
        await callback.message.edit_text(
            f"✅ Отправлено {sent_count} файлов логов из {len(available_logs)}!",
            reply_markup=get_back_keyboard("admin_stats")
        )
        
        logger.log_admin_action(callback.from_user.id, f"downloaded all logs ({sent_count} files)")
        
    except Exception as e:
        logger.error(f"Error sending all logs: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при отправке логов: {str(e)}",
            reply_markup=get_back_keyboard("get_logs")
        )
    await callback.answer()