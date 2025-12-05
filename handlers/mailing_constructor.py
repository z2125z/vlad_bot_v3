from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from services.database import db
from utils.helpers import (
    get_mailing_type_keyboard, 
    get_back_keyboard, 
    format_mailing_preview, 
    get_mailing_preview_keyboard, 
    get_mailing_actions_keyboard, 
    get_skip_trigger_keyboard,
    get_mailing_buttons_keyboard
)
import config
from services.logger import logger
import json

router = Router()

class MailingConstructor(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_buttons = State()
    waiting_for_confirmation = State()
    editing_title = State()
    editing_text = State()
    editing_media = State()
    editing_buttons = State()
    waiting_for_trigger_word = State()
    editing_trigger_word = State()

# Начало создания рассылки
@router.callback_query(F.data == "create_mailing")
async def create_mailing_start(callback: CallbackQuery, state: FSMContext):
    if not callback.from_user.id in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.clear()
    await state.set_state(MailingConstructor.waiting_for_title)
    
    await callback.message.answer(
        "📝 <b>Создание новой рассылки</b>\n\n"
        "Введите название рассылки (максимум 200 символов):",
        reply_markup=get_back_keyboard("admin_mailings"),
        parse_mode="HTML"
    )
    await callback.answer()

# Получение названия
@router.message(MailingConstructor.waiting_for_title)
async def mailing_get_title(message: Message, state: FSMContext):
    if len(message.text) > 200:
        await message.answer("❌ Слишком длинное название. Максимум 200 символов.")
        return
        
    await state.update_data(title=message.text.strip())
    await state.set_state(MailingConstructor.waiting_for_text)
    
    await message.answer(
        "📄 Введите текст рассылки. Можно использовать HTML разметку:\n\n"
        "<i>Примеры разметки:</i>\n"
        "<b>жирный</b>\n"
        "<i>курсив</i>\n"
        "<u>подчеркнутый</u>\n"
        "<code>моноширинный</code>\n"
        "<a href='https://example.com'>ссылка</a>",
        reply_markup=get_back_keyboard("admin_mailings"),
        parse_mode="HTML"
    )

# Получение текста
@router.message(MailingConstructor.waiting_for_text)
async def mailing_get_text(message: Message, state: FSMContext):
    if not message.text and not message.html_text:
        await message.answer("❌ Текст не может быть пустым.")
        return
        
    text_content = message.html_text or message.text
    await state.update_data(message_text=text_content)
    await state.set_state(MailingConstructor.waiting_for_media)
    
    await message.answer(
        "🎬 Выберите тип контента для рассылки:",
        reply_markup=get_mailing_type_keyboard()
    )

# Обработка выбора типа медиа
@router.callback_query(MailingConstructor.waiting_for_media, F.data.startswith("mailing_type_"))
async def mailing_select_media_type(callback: CallbackQuery, state: FSMContext):
    media_type = callback.data.replace("mailing_type_", "")
    
    await state.update_data(message_type=media_type)
    
    if media_type == "text":
        await state.update_data(media_file_id=None)
        await state.set_state(MailingConstructor.waiting_for_buttons)
        await mailing_ask_for_buttons(callback, state)
    else:
        media_names = {
            "photo": "🖼️ фото",
            "video": "🎥 видео", 
            "document": "📎 документ",
            "voice": "🎤 голосовое сообщение",
            "video_note": "📹 видео-сообщение"
        }
        
        await callback.message.edit_text(
            f"📎 Отправьте {media_names.get(media_type, 'медиа')} для рассылки:",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    await callback.answer()

# Получение медиа-файла
@router.message(
    MailingConstructor.waiting_for_media,
    F.content_type.in_({
        ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT,
        ContentType.VOICE, ContentType.VIDEO_NOTE
    })
)
async def mailing_get_media(message: Message, state: FSMContext):
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
        await state.set_state(MailingConstructor.waiting_for_buttons)
        await mailing_ask_for_buttons(message, state)
    else:
        await message.answer(f"❌ Вы отправили неверный тип медиа. Ожидается: {media_type}")

async def mailing_ask_for_buttons(update, state: FSMContext):
    """Спросить про кнопки для рассылки"""
    text = (
        "🔘 <b>Добавление кнопок</b>\n\n"
        "Хотите добавить кнопки под сообщением?\n\n"
        "<i>Типы кнопок:</i>\n"
        "• URL кнопки - ссылки на сайты\n"
        "• Callback кнопки - для действий внутри бота\n\n"
        "Выберите действие:"
    )
    
    if update.__class__.__name__ == "CallbackQuery":
        await update.message.answer(text, parse_mode="HTML", reply_markup=get_mailing_buttons_keyboard())
    else:
        await update.answer(text, parse_mode="HTML", reply_markup=get_mailing_buttons_keyboard())

# Обработка кнопок
@router.callback_query(MailingConstructor.waiting_for_buttons, F.data == "mailing_add_buttons")
async def mailing_add_buttons(callback: CallbackQuery, state: FSMContext):
    await state.update_data(buttons=[])
    await callback.message.answer(
        "🔘 <b>Добавление кнопок</b>\n\n"
        "Отправьте кнопки в формате JSON.\n"
        "<i>Пример URL кнопки:</i>\n"
        '<code>[{"text": "Открыть сайт", "url": "https://example.com"}]</code>\n\n'
        "<i>Пример Callback кнопки:</i>\n"
        '<code>[{"text": "Подробнее", "callback_data": "more_info"}]</code>\n\n'
        "Или отправьте 'готово' для завершения:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard("admin_mailings")
    )
    await callback.answer()

@router.callback_query(MailingConstructor.waiting_for_buttons, F.data == "mailing_skip_buttons")
async def mailing_skip_buttons(callback: CallbackQuery, state: FSMContext):
    await state.update_data(buttons=[])
    await mailing_finalize(callback, state)
    await callback.answer()

@router.message(MailingConstructor.waiting_for_buttons)
async def mailing_get_buttons(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'готово':
        data = await state.get_data()
        if 'buttons' not in data:
            await state.update_data(buttons=[])
        await mailing_finalize(message, state)
        return
    
    try:
        buttons = json.loads(message.text)
        if not isinstance(buttons, list):
            raise ValueError("Кнопки должны быть списком")
        
        for button in buttons:
            if not isinstance(button, dict):
                raise ValueError("Каждая кнопка должна быть словарем")
            if 'text' not in button:
                raise ValueError("Кнопка должна содержать 'text'")
            if not ('url' in button or 'callback_data' in button):
                raise ValueError("Кнопка должна содержать 'url' или 'callback_data'")
        
        await state.update_data(buttons=buttons)
        await message.answer(
            f"✅ Добавлено {len(buttons)} кнопок. Отправьте 'готово' для завершения или отправьте новые кнопки:"
        )
        
    except json.JSONDecodeError:
        await message.answer("❌ Неверный формат JSON. Проверьте синтаксис.")
    except ValueError as e:
        await message.answer(f"❌ Ошибка в формате кнопок: {str(e)}")

# Финальный шаг - предпросмотр и сохранение
async def mailing_finalize(update, state: FSMContext):
    data = await state.get_data()
    
    # Создаем рассылку в БД
    mailing = db.create_mailing(
        title=data['title'],
        message_text=data['message_text'],
        message_type=data.get('message_type', 'text'),
        media_file_id=data.get('media_file_id'),
        buttons=data.get('buttons', []),
        status="draft"
    )
    
    if not mailing:
        if update.__class__.__name__ == "CallbackQuery":
            await update.message.answer("❌ Ошибка при создании рассылки")
        else:
            await update.answer("❌ Ошибка при создании рассылки")
        await state.clear()
        return
    
    await state.update_data(mailing_id=mailing['id'])
    
    # Спрашиваем про кодовое слово
    await state.set_state(MailingConstructor.waiting_for_trigger_word)
    
    if update.__class__.__name__ == "CallbackQuery":
        message = update.message
    else:
        message = update
        
    await message.answer(
        "🔤 <b>Настройка рассылки по запросу</b>\n\n"
        "Хотите сделать эту рассылку доступной по кодовому слову?\n\n"
        "Отправьте кодовое слово (например: <code>прайс</code>, <code>услуги</code>) или нажмите 'Пропустить':",
        parse_mode="HTML",
        reply_markup=get_skip_trigger_keyboard()
    )

# Обработка кодового слова
@router.message(MailingConstructor.waiting_for_trigger_word)
async def mailing_get_trigger_word(message: Message, state: FSMContext):
    trigger_word = message.text.strip().lower()
    
    if len(trigger_word) > 50:
        await message.answer("❌ Слишком длинное кодовое слово. Максимум 50 символов.")
        return
    
    data = await state.get_data()
    mailing_id = data['mailing_id']
    
    # Обновляем рассылку
    db.update_mailing(mailing_id, 
                     trigger_word=trigger_word, 
                     is_trigger_mailing=True)
    
    await mailing_show_preview(message, state)

# Пропуск кодового слова
@router.callback_query(MailingConstructor.waiting_for_trigger_word, F.data == "skip_trigger")
async def mailing_skip_trigger_word(callback: CallbackQuery, state: FSMContext):
    await mailing_show_preview(callback, state)
    await callback.answer()

# Функция показа превью
async def mailing_show_preview(update, state: FSMContext):
    data = await state.get_data()
    mailing_id = data['mailing_id']
    
    await state.set_state(MailingConstructor.waiting_for_confirmation)
    
    mailing = db.get_mailing(mailing_id)
    preview_text = format_mailing_preview(mailing)
    
    if update.__class__.__name__ == "CallbackQuery":
        message = update.message
        await message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_preview_keyboard(mailing_id)
        )
    else:
        message = update
        await message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_preview_keyboard(mailing_id)
        )

# Сохранение как черновика
@router.callback_query(F.data.startswith("save_draft_"))
async def save_mailing_draft(callback: CallbackQuery, state: FSMContext):
    try:
        mailing_id = int(callback.data.replace("save_draft_", ""))
        db.change_mailing_status(mailing_id, "draft")
        await state.clear()
        
        await callback.answer("✅ Рассылка сохранена как черновик")
        await callback.message.answer(
            "✅ Рассылка сохранена как черновик\n\n"
            "Вы можете найти её в разделе 'Черновики'",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"saved mailing {mailing_id} as draft")
    except Exception as e:
        logger.error(f"Error saving draft: {e}")
        await callback.answer("❌ Ошибка при сохранении")

# Активация рассылки
@router.callback_query(F.data.startswith("activate_mailing_"))
async def activate_mailing(callback: CallbackQuery, state: FSMContext):
    try:
        mailing_id = int(callback.data.replace("activate_mailing_", ""))
        db.change_mailing_status(mailing_id, "active")
        await state.clear()
        
        await callback.answer("✅ Рассылка активирована")
        await callback.message.answer(
            "✅ Рассылка активирована и готова к отправке\n\n"
            "Теперь вы можете отправить её через раздел 'Отправить рассылку'",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"activated mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error activating mailing: {e}")
        await callback.answer("❌ Ошибка при активации")

# Отправка рассылки сразу
@router.callback_query(F.data.startswith("send_now_"))
async def send_mailing_now(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        mailing_id = int(callback.data.replace("send_now_", ""))
        await state.clear()
        
        from services.mailing import MailingService
        mailing_service = MailingService(bot)
        
        await callback.message.answer("🔄 Подготовка к отправке...")
        
        success, success_count, total_count = await mailing_service.broadcast_mailing(
            mailing_id=mailing_id,
            target_group="all"
        )
        
        if success:
            await callback.message.answer(
                f"✅ <b>Рассылка отправлена!</b>\n\n"
                f"📤 Отправлено: {success_count}/{total_count} сообщений\n"
                f"📊 Успешных: {(success_count/total_count*100 if total_count > 0 else 0):.1f}%\n\n"
                f"Статистику можно посмотреть в разделе 'Статистика рассылок'",
                parse_mode="HTML",
                reply_markup=get_back_keyboard("admin_mailings")
            )
        else:
            await callback.message.answer(
                "❌ Ошибка при отправке рассылки",
                reply_markup=get_back_keyboard("admin_mailings")
            )
        logger.log_admin_action(callback.from_user.id, f"sent mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error sending mailing: {e}")
        await callback.answer("❌ Ошибка при отправке")

# Просмотр конкретной рассылки
@router.callback_query(F.data.startswith("view_mailing_"))
async def view_mailing(callback: CallbackQuery):
    try:
        mailing_id = int(callback.data.replace("view_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        preview_text = format_mailing_preview(mailing)
        await callback.message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_actions_keyboard(mailing_id, mailing['status'])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error viewing mailing: {e}")
        await callback.answer("❌ Ошибка при загрузке")

# Редактирование названия рассылки
@router.callback_query(F.data.startswith("edit_mailing_"))
async def edit_mailing_start(callback: CallbackQuery, state: FSMContext):
    try:
        mailing_id = int(callback.data.replace("edit_mailing_", ""))
        mailing = db.get_mailing(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена")
            return
        
        await state.update_data(editing_mailing_id=mailing_id)
        await state.set_state(MailingConstructor.editing_title)
        
        await callback.message.answer(
            f"✏️ <b>Редактирование рассылки</b>\n\n"
            f"Текущее название: <b>{mailing['title']}</b>\n\n"
            f"Введите новое название рассылки:",
            parse_mode="HTML",
            reply_markup=get_back_keyboard(f"view_mailing_{mailing_id}")
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error starting edit mailing: {e}")
        await callback.answer("❌ Ошибка")

# Получение нового названия
@router.message(MailingConstructor.editing_title)
async def edit_mailing_title(message: Message, state: FSMContext):
    if len(message.text) > 200:
        await message.answer("❌ Слишком длинное название. Максимум 200 символов.")
        return
    
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    db.update_mailing(mailing_id, title=message.text.strip())
    await state.set_state(MailingConstructor.editing_text)
    
    mailing = db.get_mailing(mailing_id)
    text_preview = mailing['message_text'][:100] + "..." if len(mailing['message_text']) > 100 else mailing['message_text']
    
    await message.answer(
        f"✅ Название обновлено!\n\n"
        f"Текущий текст: <b>{text_preview}</b>\n\n"
        f"Введите новый текст рассылки:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard(f"view_mailing_{mailing_id}")
    )

# Получение нового текста
@router.message(MailingConstructor.editing_text)
async def edit_mailing_text(message: Message, state: FSMContext):
    if not message.text and not message.html_text:
        await message.answer("❌ Текст не может быть пустым.")
        return
    
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    text_content = message.html_text or message.text
    db.update_mailing(mailing_id, message_text=text_content)
    
    await state.set_state(MailingConstructor.editing_media)
    
    mailing = db.get_mailing(mailing_id)
    
    await message.answer(
        f"✅ Текст обновлен!\n\n"
        f"Текущий тип контента: <b>{mailing['message_type']}</b>\n\n"
        f"Выберите новый тип контента или нажмите 'Пропустить' чтобы оставить текущий:",
        parse_mode="HTML",
        reply_markup=get_mailing_type_keyboard()
    )

# Обработка выбора нового типа медиа при редактировании
@router.callback_query(MailingConstructor.editing_media, F.data.startswith("mailing_type_"))
async def edit_mailing_media_type(callback: CallbackQuery, state: FSMContext):
    media_type = callback.data.replace("mailing_type_", "")
    
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    if media_type == "text":
        db.update_mailing(mailing_id, message_type="text", media_file_id=None)
        await state.set_state(MailingConstructor.editing_buttons)
        await edit_mailing_ask_for_buttons(callback, state)
    else:
        await state.update_data(editing_media_type=media_type)
        media_names = {
            "photo": "🖼️ фото",
            "video": "🎥 видео", 
            "document": "📎 документ",
            "voice": "🎤 голосовое сообщение",
            "video_note": "📹 видео-сообщение"
        }
        
        await callback.message.answer(
            f"📎 Отправьте {media_names.get(media_type, 'медиа')} для рассылки:",
            reply_markup=get_back_keyboard(f"view_mailing_{mailing_id}")
        )
    await callback.answer()

async def edit_mailing_ask_for_buttons(callback, state):
    """Спросить про обновление кнопок при редактировании"""
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    mailing = db.get_mailing(mailing_id)
    
    text = (
        f"🔘 <b>Обновление кнопок</b>\n\n"
        f"Текущее количество кнопок: {len(mailing['buttons'])}\n\n"
        "Хотите изменить кнопки под сообщением?\n\n"
        "Выберите действие:"
    )
    
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_mailing_buttons_keyboard())

# Получение нового медиа при редактировании
@router.message(
    MailingConstructor.editing_media,
    F.content_type.in_({
        ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT,
        ContentType.VOICE, ContentType.VIDEO_NOTE
    })
)
async def edit_mailing_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media_type = data.get('editing_media_type')
    mailing_id = data.get('editing_mailing_id')
    
    if not media_type:
        await message.answer("❌ Сначала выберите тип медиа через меню.")
        return
    
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
        db.update_mailing(mailing_id, message_type=media_type, media_file_id=media_file_id)
        await state.set_state(MailingConstructor.editing_buttons)
        await edit_mailing_ask_for_buttons(message, state)
    else:
        await message.answer(f"❌ Вы отправили неверный тип медиа. Ожидается: {media_type}")

# Обработка кнопок при редактировании
@router.callback_query(MailingConstructor.editing_buttons, F.data == "mailing_add_buttons")
async def edit_mailing_add_buttons(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔘 <b>Обновление кнопок</b>\n\n"
        "Отправьте новые кнопки в формате JSON.\n"
        "<i>Пример URL кнопки:</i>\n"
        '<code>[{"text": "Открыть сайт", "url": "https://example.com"}]</code>\n\n'
        "<i>Пример Callback кнопки:</i>\n"
        '<code>[{"text": "Подробнее", "callback_data": "more_info"}]</code>\n\n'
        "Или отправьте 'готово' для завершения:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(MailingConstructor.editing_buttons, F.data == "mailing_skip_buttons")
async def edit_mailing_skip_buttons(callback: CallbackQuery, state: FSMContext):
    await edit_mailing_finalize(callback, state)
    await callback.answer()

@router.message(MailingConstructor.editing_buttons)
async def edit_mailing_get_buttons(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'готово':
        await edit_mailing_finalize(message, state)
        return
    
    try:
        buttons = json.loads(message.text)
        if not isinstance(buttons, list):
            raise ValueError("Кнопки должны быть списком")
        
        for button in buttons:
            if not isinstance(button, dict):
                raise ValueError("Каждая кнопка должна быть словарем")
            if 'text' not in button:
                raise ValueError("Кнопка должна содержать 'text'")
            if not ('url' in button or 'callback_data' in button):
                raise ValueError("Кнопка должна содержать 'url' или 'callback_data'")
        
        data = await state.get_data()
        mailing_id = data.get('editing_mailing_id')
        
        db.update_mailing(mailing_id, buttons=buttons)
        await message.answer(
            f"✅ Обновлено {len(buttons)} кнопок. Отправьте 'готово' для завершения или отправьте новые кнопки:"
        )
        
    except json.JSONDecodeError:
        await message.answer("❌ Неверный формат JSON. Проверьте синтаксис.")
    except ValueError as e:
        await message.answer(f"❌ Ошибка в формате кнопок: {str(e)}")

# Финальный шаг при редактировании
async def edit_mailing_finalize(update, state: FSMContext):
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    mailing = db.get_mailing(mailing_id)
    
    # Спрашиваем про обновление кодового слова
    await state.set_state(MailingConstructor.editing_trigger_word)
    
    current_word = mailing.get('trigger_word', 'Не установлено')
    
    if update.__class__.__name__ == "CallbackQuery":
        message = update.message
    else:
        message = update
        
    await message.answer(
        f"🔤 <b>Обновление кодового слова</b>\n\n"
        f"Текущее кодовое слово: <code>{current_word}</code>\n\n"
        "Отправьте новое кодовое слово или нажмите 'Пропустить':",
        parse_mode="HTML",
        reply_markup=get_skip_trigger_keyboard()
    )

# Обработка нового кодового слова при редактировании
@router.message(MailingConstructor.editing_trigger_word)
async def edit_mailing_trigger_word(message: Message, state: FSMContext):
    trigger_word = message.text.strip().lower()
    
    if len(trigger_word) > 50:
        await message.answer("❌ Слишком длинное кодовое слово. Максимум 50 символов.")
        return
    
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    # Обновляем рассылку
    db.update_mailing(mailing_id, 
                     trigger_word=trigger_word, 
                     is_trigger_mailing=bool(trigger_word))
    
    await edit_mailing_show_final(message, state)

# Пропуск при редактировании
@router.callback_query(MailingConstructor.editing_trigger_word, F.data == "skip_trigger")
async def edit_mailing_skip_trigger_word(callback: CallbackQuery, state: FSMContext):
    await edit_mailing_show_final(callback, state)
    await callback.answer()

# Финальный показ после редактирования
async def edit_mailing_show_final(update, state: FSMContext):
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    mailing = db.get_mailing(mailing_id)
    preview_text = format_mailing_preview(mailing)
    
    if update.__class__.__name__ == "CallbackQuery":
        message = update.message
        await message.answer(
            "✅ Рассылка успешно обновлена!\n\n" + preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_actions_keyboard(mailing_id, mailing['status'])
        )
    else:
        message = update
        await message.answer(
            "✅ Рассылка успешно обновлена!\n\n" + preview_text,
            parse_mode="HTML",
            reply_markup=get_mailing_actions_keyboard(mailing_id, mailing['status'])
        )
    
    await state.clear()

# Архивирование рассылки
@router.callback_query(F.data.startswith("archive_mailing_"))
async def archive_mailing(callback: CallbackQuery):
    try:
        mailing_id = int(callback.data.replace("archive_mailing_", ""))
        db.change_mailing_status(mailing_id, "archived")
        
        await callback.answer("✅ Рассылка перемещена в архив")
        await callback.message.answer(
            "✅ Рассылка перемещена в архив",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"archived mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error archiving mailing: {e}")
        await callback.answer("❌ Ошибка при архивировании")

# Удаление рассылки
@router.callback_query(F.data.startswith("delete_mailing_"))
async def delete_mailing(callback: CallbackQuery):
    try:
        mailing_id = int(callback.data.replace("delete_mailing_", ""))
        db.change_mailing_status(mailing_id, "deleted")
        
        await callback.answer("✅ Рассылка удалена")
        await callback.message.answer(
            "✅ Рассылка удалена",
            reply_markup=get_back_keyboard("admin_mailings")
        )
        logger.log_admin_action(callback.from_user.id, f"deleted mailing {mailing_id}")
    except Exception as e:
        logger.error(f"Error deleting mailing: {e}")
        await callback.answer("❌ Ошибка при удалении")

# Пропуск редактирования медиа
@router.callback_query(F.data.startswith("skip_edit_"))
async def skip_edit_media(callback: CallbackQuery, state: FSMContext):
    try:
        mailing_id = int(callback.data.replace("skip_edit_", ""))
        await state.set_state(MailingConstructor.editing_buttons)
        await edit_mailing_ask_for_buttons(callback, state)
        await callback.answer("✅ Изменения сохранены")
    except Exception as e:
        logger.error(f"Error skipping edit: {e}")
        await callback.answer("❌ Ошибка")