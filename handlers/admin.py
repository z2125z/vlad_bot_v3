from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import db
from services.mailing import MailingService
from utils.helpers import (
    get_admin_keyboard, 
    get_mailings_keyboard, 
    get_back_keyboard,
    format_user_stats,
    format_mailing_stats
)
from datetime import datetime, timedelta
import config

router = Router()

class MailingState(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_confirmation = State()

# Проверка админа
def is_admin(user_id: int):
    return user_id in config.ADMIN_IDS

# Админ панель
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(
        "👨‍💻 <b>Админ панель</b>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

# Статистика пользователей
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    users_count = db.get_user_count()
    
    # Активные за сегодня (упрощенная версия)
    active_today = users_count  # В реальности нужно считать по last_activity
    
    await callback.message.edit_text(
        format_user_stats(users_count, active_today),
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )

# Меню рассылок
@router.callback_query(F.data == "admin_mailings")
async def admin_mailings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await callback.message.edit_text(
        "📨 <b>Управление рассылками</b>",
        reply_markup=get_mailings_keyboard(),
        parse_mode="HTML"
    )

# Создание рассылки - шаг 1
@router.callback_query(F.data == "create_mailing")
async def create_mailing_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.set_state(MailingState.waiting_for_title)
    await callback.message.edit_text(
        "📝 Введите название рассылки:",
        reply_markup=get_back_keyboard()
    )

# Шаг 2 - получение названия
@router.message(MailingState.waiting_for_title)
async def mailing_get_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(MailingState.waiting_for_content)
    
    await message.answer(
        "📄 Теперь отправьте текст рассылки. Можно использовать HTML разметку.",
        reply_markup=get_back_keyboard()
    )

# Шаг 3 - получение контента
@router.message(MailingState.waiting_for_content)
async def mailing_get_content(message: Message, state: FSMContext, bot: Bot):
    mailing_data = await state.get_data()
    
    # Определяем тип сообщения
    message_type = "text"
    file_id = None
    
    if message.photo:
        message_type = "photo"
        file_id = message.photo[-1].file_id
        text = message.caption or ""
    elif message.document:
        message_type = "document"
        file_id = message.document.file_id
        text = message.caption or ""
    else:
        text = message.text or message.html_text or ""
    
    # Создаем рассылку в БД
    mailing = db.create_mailing(
        title=mailing_data['title'],
        message_text=text,
        message_type=message_type,
        file_id=file_id
    )
    
    await state.update_data(mailing_id=mailing.id)
    await state.set_state(MailingState.waiting_for_confirmation)
    
    # Показываем превью
    preview_text = f"📋 <b>Превью рассылки:</b>\n\n{text}"
    
    try:
        if message_type == "text":
            await message.answer(preview_text, parse_mode="HTML")
        elif message_type == "photo":
            await message.answer_photo(file_id, caption=preview_text, parse_mode="HTML")
        elif message_type == "document":
            await message.answer_document(file_id, caption=preview_text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка отображения превью: {e}")
        await state.clear()
        return
    
    # Кнопки подтверждения
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="✅ Начать рассылку", callback_data="confirm_mailing"))
    keyboard.add(InlineKeyboardButton(text="❌ Отменить", callback_data="admin_main"))
    
    await message.answer(
        "Начать рассылку?",
        reply_markup=keyboard.as_markup()
    )

# Подтверждение рассылки
@router.callback_query(F.data == "confirm_mailing")
async def confirm_mailing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    mailing_data = await state.get_data()
    await state.clear()
    
    mailing_service = MailingService(bot)
    users = db.get_all_users()
    
    await callback.message.edit_text("🔄 Начинаю рассылку...")
    
    success_count, total_count = await mailing_service.broadcast_mailing(
        mailing_id=mailing_data['mailing_id'],
        users=users
    )
    
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {success_count}/{total_count}\n"
        f"📊 Успешных: {(success_count/total_count*100 if total_count > 0 else 0):.1f}%"
    )

# Назад в главное меню
@router.callback_query(F.data == "admin_main")
async def admin_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "👨‍💻 <b>Админ панель</b>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )