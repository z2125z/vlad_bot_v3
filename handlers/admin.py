from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from services.database import db
from services.mailing import MailingService
from services.excel_export import ExcelExporter  # Добавляем импорт
from utils.helpers import (
    get_admin_main_keyboard,
    get_stats_keyboard,
    get_mailings_keyboard,
    get_users_keyboard,
    get_target_groups_keyboard,
    get_back_keyboard,
    format_stats_overview,
    format_users_stats,
    format_mailings_stats
)
import config
from datetime import datetime, timedelta
import os

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

# Общая статистика
@router.callback_query(F.data == "stats_overview")
async def stats_overview(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        stats_text = format_stats_overview()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики: {e}",
            reply_markup=get_back_keyboard("admin_stats")
        )

# Статистика пользователей
@router.callback_query(F.data == "stats_users")
async def stats_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        stats_text = format_users_stats()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики пользователей: {e}",
            reply_markup=get_back_keyboard("admin_stats")
        )

# Статистика рассылок
@router.callback_query(F.data == "stats_mailings")
async def stats_mailings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        stats_text = format_mailings_stats()
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_back_keyboard("admin_stats"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке статистики рассылок: {e}",
            reply_markup=get_back_keyboard("admin_stats")
        )

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

# Активные рассылки
@router.callback_query(F.data == "mailings_active")
async def mailings_active(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        mailings = db.get_mailings_by_status('active')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет активных рассылок",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        text = "✅ <b>Активные рассылки:</b>\n\n"
        for mailing in mailings:
            stats = db.get_mailing_stats(mailing.id)
            text += f"📨 {mailing.title}\n"
            text += f"   📊 Отправлено: {stats['delivered']}/{stats['total_sent']}\n"
            text += f"   🕐 Создана: {mailing.created_at.strftime('%d.%m.%Y')}\n"
            text += f"   [ID: {mailing.id}]\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_mailings"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке активных рассылок: {e}",
            reply_markup=get_back_keyboard("admin_mailings")
        )

# Черновики
@router.callback_query(F.data == "mailings_drafts")
async def mailings_drafts(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        mailings = db.get_mailings_by_status('draft')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет черновиков рассылок",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        text = "📝 <b>Черновики рассылок:</b>\n\n"
        for mailing in mailings:
            text += f"📄 {mailing.title}\n"
            text += f"   🕐 Создан: {mailing.created_at.strftime('%d.%m.%Y')}\n"
            text += f"   [ID: {mailing.id}]\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_mailings"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке черновиков: {e}",
            reply_markup=get_back_keyboard("admin_mailings")
        )

# Архив рассылок
@router.callback_query(F.data == "mailings_archive")
async def mailings_archive(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        mailings = db.get_mailings_by_status('archived')
        
        if not mailings:
            await callback.message.edit_text(
                "❌ Нет рассылок в архиве",
                reply_markup=get_back_keyboard("admin_mailings")
            )
            return
        
        text = "📁 <b>Архив рассылок:</b>\n\n"
        for mailing in mailings:
            stats = db.get_mailing_stats(mailing.id)
            text += f"📨 {mailing.title}\n"
            text += f"   📊 Отправлено: {stats['delivered']}/{stats['total_sent']}\n"
            text += f"   🕐 Создана: {mailing.created_at.strftime('%d.%m.%Y')}\n"
            text += f"   [ID: {mailing.id}]\n\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_mailings"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке архива: {e}",
            reply_markup=get_back_keyboard("admin_mailings")
        )

# Меню отправки рассылки
@router.callback_query(F.data == "mailings_send")
async def mailings_send(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
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
            keyboard.add(InlineKeyboardButton(
                text=f"📨 {mailing.title}",
                callback_data=f"select_mailing_{mailing.id}"
            ))
        
        keyboard.add(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_mailings"))
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке рассылок: {e}",
            reply_markup=get_back_keyboard("admin_mailings")
        )

# Выбор целевой группы
@router.callback_query(F.data.startswith("select_mailing_"))
async def select_mailing_target(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        mailing_id = int(callback.data.replace("select_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        users_count = db.get_user_count()
        active_today = db.get_active_users_count_today()
        new_users = db.get_new_users_count(days=7)
        
        await callback.message.edit_text(
            f"🎯 <b>Выбор целевой группы</b>\n\n"
            f"📨 Рассылка: <b>{mailing.title}</b>\n\n"
            f"👥 Доступные группы:\n"
            f"   • Все пользователи: {users_count} чел.\n"
            f"   • Активные сегодня: {active_today} чел.\n"
            f"   • Новые пользователи (7 дней): {new_users} чел.",
            reply_markup=get_target_groups_keyboard(mailing_id),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при выборе рассылки: {e}",
            reply_markup=get_back_keyboard("mailings_send")
        )

# Запуск рассылки
@router.callback_query(F.data.startswith("target_"))
async def start_mailing_broadcast(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        data_parts = callback.data.split("_")
        if len(data_parts) < 3:
            await callback.answer("❌ Ошибка в данных")
            return
            
        target_group = data_parts[1]  # all, active или new
        mailing_id = int(data_parts[2])
        
        mailing = db.get_mailing(mailing_id)
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        mailing_service = MailingService(bot)
        
        await callback.message.edit_text("🔄 Начинаю рассылку...")
        
        success, success_count, total_count = await mailing_service.broadcast_mailing(
            mailing_id=mailing_id,
            target_group=target_group
        )
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📋 <b>Рассылка:</b> {mailing.title}\n"
                f"🎯 <b>Целевая группа:</b> {get_target_group_name(target_group)}\n"
                f"📤 <b>Отправлено:</b> {success_count}/{total_count} сообщений\n"
                f"📊 <b>Успешных:</b> {(success_count/total_count*100 if total_count > 0 else 0):.1f}%",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("admin_mailings")
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка при рассылке",
                reply_markup=get_back_keyboard("admin_mailings")
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при запуске рассылки: {e}",
            reply_markup=get_back_keyboard("admin_mailings")
        )

def get_target_group_name(target_group: str) -> str:
    """Получить читаемое название целевой группы"""
    names = {
        "all": "Все пользователи",
        "active": "Активные сегодня", 
        "new": "Новые пользователи"
    }
    return names.get(target_group, "Неизвестная группа")

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

# Список пользователей
@router.callback_query(F.data == "users_list")
async def users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        users = db.get_all_users()[:50]  # Ограничим показ 50 пользователями
        
        if not users:
            await callback.message.edit_text(
                "❌ Нет пользователей",
                reply_markup=get_back_keyboard("admin_users")
            )
            return
        
        text = "👥 <b>Последние пользователи:</b>\n\n"
        for user in users[:10]:  # Покажем первых 10
            status = "🟢" if user.is_active else "🔴"
            text += f"{status} {user.full_name or 'Без имени'}\n"
            text += f"   👤 @{user.username or 'без username'}\n"
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
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке пользователей: {e}",
            reply_markup=get_back_keyboard("admin_users")
        )

# Активные сегодня
@router.callback_query(F.data == "users_active_today")
async def users_active_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        users = db.get_active_users_today()[:20]  # Ограничим показ
        
        if not users:
            await callback.message.edit_text(
                "❌ Нет активных пользователей за сегодня",
                reply_markup=get_back_keyboard("admin_users")
            )
            return
        
        text = "📅 <b>Активные пользователи сегодня:</b>\n\n"
        for user in users[:10]:  # Покажем первых 10
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
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке активных пользователей: {e}",
            reply_markup=get_back_keyboard("admin_users")
        )

# Аналитика активности
@router.callback_query(F.data == "users_analytics")
async def users_analytics(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        total_users = db.get_user_count()
        active_today = db.get_active_users_count_today()
        active_week = db.get_active_users_count_week()
        new_today = db.get_new_users_count(days=1)
        new_week = db.get_new_users_count(days=7)
        
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

📈 <b>Процент активности:</b>
   • За сегодня: {today_rate:.1f}%
   • За неделю: {week_rate:.1f}%

📅 <b>Тенденции:</b>
   • Рост за неделю: +{new_week} пользователей
"""
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_users"),
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке аналитики: {e}",
            reply_markup=get_back_keyboard("admin_users")
        )

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

# Добавляем новый обработчик для экспорта в Excel
@router.callback_query(F.data == "export_excel")
async def export_to_excel(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    try:
        await callback.message.edit_text("📊 Генерируем Excel отчет... Это может занять несколько секунд.")
        
        exporter = ExcelExporter()
        filepath = exporter.generate_full_report()
        
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
        
        # Удаляем временный файл после отправки
        try:
            os.remove(filepath)
        except:
            pass
            
        # Очищаем старые экспорты
        exporter.cleanup_old_exports()
        
        await callback.message.edit_text(
            "✅ <b>Excel отчет успешно сгенерирован и отправлен!</b>",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("admin_stats")
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при генерации отчета: {e}",
            reply_markup=get_back_keyboard("admin_stats")
        )