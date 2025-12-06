from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import db
from utils.helpers import get_back_keyboard, get_mailing_type_keyboard
import config
import html
from services.logger import logger

router = Router()

class WelcomeEditor(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_confirmation = State()

# Редактирование приветственного сообщения
@router.callback_query(F.data == "edit_welcome")
async def edit_welcome_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования приветственного сообщения"""
    if not callback.from_user.id in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.clear()
    
    current_welcome = db.get_welcome_message()
    trigger_mailings = db.get_active_trigger_mailings()
    
    # Формируем текст с информацией о доступных кодовых словах
    trigger_info = ""
    if trigger_mailings:
        trigger_info = "\n\n🔤 <b>Активные кодовые слова:</b>\n"
        for mailing in trigger_mailings:
            if mailing and mailing.get('trigger_word'):
                trigger_word = mailing.get('trigger_word')
                # Проверяем, что trigger_word не None и не пустой
                if trigger_word and trigger_word.strip():
                    safe_word = html.escape(trigger_word)
                    safe_title = html.escape(mailing.get('title', 'Без названия'))
                    trigger_info += f"• <code>{safe_word}</code> - {safe_title}\n"
    
    if current_welcome:
        # Обрезаем текст для отображения
        message_text = current_welcome.get('message_text', '')
        preview_text = message_text[:500] + "..." if len(message_text) > 500 else message_text
        safe_preview = html.escape(preview_text)
        
        text = (
            "👋 <b>Текущее приветственное сообщение:</b>\n\n"
            f"{safe_preview}{trigger_info}\n\n"
            "Выберите действие:"
        )
    else:
        text = f"👋 <b>Приветственное сообщение еще не настроено</b>{trigger_info}\n\nСоздайте новое сообщение:"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Редактировать текст", callback_data="welcome_edit_text")
    keyboard.button(text="🎬 Изменить медиа", callback_data="welcome_edit_media")
    keyboard.button(text="👁️ Просмотр", callback_data="welcome_preview")
    keyboard.button(text="📋 Список кодовых слов", callback_data="trigger_words_list")
    keyboard.button(text="🔙 Назад", callback_data="admin_main")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# Список кодовых слов
@router.callback_query(F.data == "trigger_words_list")
async def trigger_words_list(callback: CallbackQuery):
    """Просмотр списка кодовых слов"""
    trigger_mailings = db.get_active_trigger_mailings()
    
    if not trigger_mailings:
        text = "❌ Нет активных рассылок по кодовым словам.\n\nСоздайте рассылку и установите для нее кодовое слово."
    else:
        text = "🔤 <b>Активные кодовые слова:</b>\n\n"
        for mailing in trigger_mailings:
            if mailing and mailing.get('trigger_word'):
                trigger_word = mailing.get('trigger_word')
                # Проверяем, что trigger_word не None и не пустой
                if trigger_word and trigger_word.strip():
                    stats = db.get_mailing_stats(mailing['id'])
                    # Безопасное экранирование HTML
                    safe_word = html.escape(trigger_word)
                    safe_title = html.escape(mailing.get('title', 'Без названия'))
                    message_preview = html.escape(mailing.get('message_text', '')[:50])
                    
                    text += f"• <b>{safe_word}</b> - {safe_title}\n"
                    text += f"  📊 Отправлено: {stats.get('delivered', 0)} раз\n"
                    text += f"  📝 Текст: {message_preview}...\n\n"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✉️ Создать новую рассылку", callback_data="create_mailing")
    keyboard.button(text="🔙 Назад", callback_data="edit_welcome")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# Начало редактирования текста
@router.callback_query(F.data == "welcome_edit_text")
async def welcome_edit_text_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования текста приветственного сообщения"""
    await state.set_state(WelcomeEditor.waiting_for_text)
    
    current_welcome = db.get_welcome_message()
    trigger_mailings = db.get_active_trigger_mailings()
    
    # Пример текста с кодовыми словами
    example_trigger_words = ""
    if trigger_mailings:
        example_trigger_words = "\n\n🔤 <b>Доступные кодовые слова для примера:</b>\n"
        for mailing in trigger_mailings[:3]:  # Показываем первые 3
            if mailing and mailing.get('trigger_word'):
                trigger_word = mailing.get('trigger_word')
                # Проверяем, что trigger_word не None и не пустой
                if trigger_word and trigger_word.strip():
                    safe_word = html.escape(trigger_word)
                    example_trigger_words += f"• <code>{safe_word}</code>\n"
    
    # Безопасное отображение текущего текста
    current_text = ""
    if current_welcome:
        message_text = current_welcome.get('message_text', '')
        current_text = html.escape(message_text[:300])
    
    await callback.message.edit_text(
        "📝 <b>Редактирование приветственного сообщения</b>\n\n"
        "Введите новый текст приветственного сообщения. Можно использовать HTML разметку.\n\n"
        "💡 <b>Совет:</b> Упомяните в тексте кодовые слова, которые пользователи могут вводить.\n"
        "Например: \"Введите <code>прайс</code> чтобы получить актуальные цены\""
        f"{example_trigger_words}\n\n"
        f"<i>Текущий текст:</i>\n{current_text if current_text else 'Не установлен'}...",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("edit_welcome")
    )
    await callback.answer()

# Получение нового текста
@router.message(WelcomeEditor.waiting_for_text)
async def welcome_get_text(message: Message, state: FSMContext):
    """Получение нового текста приветственного сообщения"""
    if not message.html_text and not message.text:
        await message.answer("❌ Текст не может быть пустым.")
        return
        
    text_content = message.html_text or message.text
    
    # Проверяем длину текста
    if len(text_content) > 4000:
        await message.answer("❌ Текст слишком длинный. Максимум 4000 символов.")
        return
    
    await state.update_data(message_text=text_content)
    await state.set_state(WelcomeEditor.waiting_for_media)
    
    await message.answer(
        "🎬 Выберите тип контента для приветственного сообщения:",
        reply_markup=get_mailing_type_keyboard()
    )

# Выбор типа медиа для приветствия
@router.callback_query(WelcomeEditor.waiting_for_media, F.data.startswith("mailing_type_"))
async def welcome_select_media_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа медиа для приветственного сообщения"""
    media_type = callback.data.replace("mailing_type_", "")
    
    await state.update_data(message_type=media_type)
    
    if media_type == "text":
        await state.update_data(media_file_id=None)
        await welcome_finalize(callback, state)
    else:
        media_names = {
            "photo": "🖼️ фото",
            "video": "🎥 видео", 
            "document": "📎 документ",
            "voice": "🎤 голосовое сообщение",
            "video_note": "📹 видео-сообщение"
        }
        
        await callback.message.edit_text(
            f"📎 Отправьте {media_names.get(media_type, 'медиа')} для приветственного сообщения:",
            reply_markup=get_back_keyboard("edit_welcome")
        )
    await callback.answer()

# Получение медиа для приветствия
@router.message(
    WelcomeEditor.waiting_for_media,
    F.content_type.in_({
        ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT,
        ContentType.VOICE, ContentType.VIDEO_NOTE
    })
)
async def welcome_get_media(message: Message, state: FSMContext):
    """Получение медиа для приветственного сообщения"""
    data = await state.get_data()
    media_type = data.get('message_type')
    
    media_file_id = None
    valid_content = False
    
    if media_type == "photo" and message.photo:
        media_file_id = message.photo[-1].file_id
        valid_content = True
    elif media_type == "video" and message.video:
        media_file_id = message.video.file_id
        valid_content = True
    elif media_type == "document" and message.document:
        media_file_id = message.document.file_id
        valid_content = True
    elif media_type == "voice" and message.voice:
        media_file_id = message.voice.file_id
        valid_content = True
    elif media_type == "video_note" and message.video_note:
        media_file_id = message.video_note.file_id
        valid_content = True
    
    if valid_content and media_file_id:
        await state.update_data(media_file_id=media_file_id)
        await welcome_finalize(message, state)
    else:
        await message.answer(f"❌ Вы отправили неверный тип медиа. Ожидается: {media_type}")

# Сохранение приветственного сообщения
async def welcome_finalize(update, state: FSMContext):
    """Сохранение приветственного сообщения"""
    data = await state.get_data()
    
    # Проверяем обязательные поля
    if 'message_text' not in data:
        if update.__class__.__name__ == "CallbackQuery":
            await update.message.answer("❌ Текст сообщения не указан")
        else:
            await update.answer("❌ Текст сообщения не указан")
        return
    
    success = db.update_welcome_message(
        message_text=data['message_text'],
        message_type=data.get('message_type', 'text'),
        media_file_id=data.get('media_file_id')
    )
    
    if success:
        if update.__class__.__name__ == "CallbackQuery":
            message = update.message
        else:
            message = update
            
        await message.answer(
            "✅ <b>Приветственное сообщение успешно обновлено!</b>\n\n"
            "Теперь новые пользователи будут получать это сообщение при команде /start",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("admin_main")
        )
        logger.log_admin_action(message.chat.id, "updated welcome message")
    else:
        if update.__class__.__name__ == "CallbackQuery":
            await update.message.answer("❌ Ошибка при обновлении приветственного сообщения")
        else:
            await update.answer("❌ Ошибка при обновлении приветственного сообщения")
    
    await state.clear()

# Просмотр приветственного сообщения
@router.callback_query(F.data == "welcome_preview")
async def welcome_preview(callback: CallbackQuery, bot: Bot):
    """Просмотр приветственного сообщения"""
    welcome = db.get_welcome_message()
    
    if not welcome:
        await callback.answer("❌ Приветственное сообщение не настроено")
        return
    
    try:
        message_text = welcome.get('message_text', '')
        media_file_id = welcome.get('media_file_id')
        message_type = welcome.get('message_type', 'text')
        
        if message_type == "text":
            await bot.send_message(
                chat_id=callback.from_user.id,
                text=message_text,
                parse_mode="HTML"
            )
        elif message_type == "photo" and media_file_id:
            await bot.send_photo(
                chat_id=callback.from_user.id,
                photo=media_file_id,
                caption=message_text,
                parse_mode="HTML"
            )
        elif message_type == "video" and media_file_id:
            await bot.send_video(
                chat_id=callback.from_user.id,
                video=media_file_id,
                caption=message_text,
                parse_mode="HTML"
            )
        elif message_type == "document" and media_file_id:
            await bot.send_document(
                chat_id=callback.from_user.id,
                document=media_file_id,
                caption=message_text,
                parse_mode="HTML"
            )
        elif message_type == "voice" and media_file_id:
            await bot.send_voice(
                chat_id=callback.from_user.id,
                voice=media_file_id,
                caption=message_text,
                parse_mode="HTML"
            )
        elif message_type == "video_note" and media_file_id:
            await bot.send_video_note(
                chat_id=callback.from_user.id,
                video_note=media_file_id
            )
            if message_text:
                await bot.send_message(
                    chat_id=callback.from_user.id,
                    text=message_text,
                    parse_mode="HTML"
                )
        
        await callback.answer("👆 Предпросмотр отправлен в чат")
        
    except Exception as e:
        logger.error(f"Error sending welcome preview: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при отправке предпросмотра")