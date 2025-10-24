from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from services.database import db
from utils.helpers import (
    get_admin_main_keyboard,
    get_stats_keyboard,
    get_mailings_keyboard,
    get_users_keyboard,
    get_mailing_actions_keyboard,
    get_target_groups_keyboard,
    get_back_keyboard,
    format_stats_overview,
    format_users_stats,
    format_mailings_stats,
    format_mailing_preview
)
import config
from datetime import datetime, timedelta

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
    
    await callback.message.edit_text(
        format_stats_overview(),
        reply_markup=get_back_keyboard("admin_stats"),
        parse_mode="HTML"
    )

# Статистика пользователей
@router.callback_query(F.data == "stats_users")
async def stats_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        format_users_stats(),
        reply_markup=get_back_keyboard("admin_stats"),
        parse_mode="HTML"
    )

# Статистика рассылок
@router.callback_query(F.data == "stats_mailings")
async def stats_mailings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        format_mailings_stats(),
        reply_markup=get_back_keyboard("admin_stats"),
        parse_mode="HTML"
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

# Черновики
@router.callback_query(F.data == "mailings_drafts")
async def mailings_drafts(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
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

# Архив рассылок
@router.callback_query(F.data == "mailings_archive")
async def mailings_archive(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
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

# Меню отправки рассылки
@router.callback_query(F.data == "mailings_send")
async def mailings_send(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
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

# Выбор целевой группы
@router.callback_query(F.data.startswith("select_mailing_"))
async def select_mailing_target(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    mailing_id = int(callback.data.replace("select_mailing_", ""))
    mailing = db.get_mailing(mailing_id)
    
    if not mailing:
        await callback.answer("❌ Рассылка не найдена")
        return
    
    users_count = db.get_user_count()
    active_today = db.get_active_users_count_today()
    
    await callback.message.edit_text(
        f"🎯 <b>Выбор целевой группы</b>\n\n"
        f"📨 Рассылка: <b>{mailing.title}</b>\n\n"
        f"👥 Доступные группы:\n"
        f"   • Все пользователи: {users_count} чел.\n"
        f"   • Активные сегодня: {active_today} чел.\n"
        f"   • Новые пользователи: {db.get_new_users_count()} чел.",
        reply_markup=get_target_groups_keyboard(mailing_id),
        parse_mode="HTML"
    )

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
        text += f"{status} {user.full_name}\n"
        text += f"   👤 @{user.username or 'без username'}\n"
        text += f"   🕐 Зарегистрирован: {user.joined_at.strftime('%d.%m.%Y')}\n\n"
    
    if len(users) > 10:
        text += f"... и еще {len(users) - 10} пользователей"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("admin_users"),
        parse_mode="HTML"
    )

# Активные сегодня
@router.callback_query(F.data == "users_active_today")
async def users_active_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    users = db.get_active_users_today()[:20]  # Ограничим показ
    
    if not users:
        await callback.message.edit_text(
            "❌ Нет активных пользователей за сегодня",
            reply_markup=get_back_keyboard("admin_users")
        )
        return
    
    text = "📅 <b>Активные пользователи сегодня:</b>\n\n"
    for user in users[:10]:  # Покажем первых 10
        text += f"🟢 {user.full_name}\n"
        text += f"   👤 @{user.username or 'без username'}\n"
        text += f"   ⏰ Был активен: {user.last_activity.strftime('%H:%M')}\n\n"
    
    if len(users) > 10:
        text += f"... и еще {len(users) - 10} пользователей"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("admin_users"),
        parse_mode="HTML"
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