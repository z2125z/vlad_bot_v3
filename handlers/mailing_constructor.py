from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import db
from utils.helpers import get_mailing_type_keyboard, get_back_keyboard, format_mailing_preview, get_mailing_preview_keyboard, get_mailing_actions_keyboard, get_skip_trigger_keyboard
import config

router = Router()

class MailingConstructor(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_confirmation = State()
    editing_title = State()
    editing_text = State()
    editing_media = State()
    waiting_for_trigger_word = State()
    editing_trigger_word = State()

# Начало создания рассылки
@router.callback_query(F.data == "create_mailing")
async def create_mailing_start(callback: CallbackQuery, state: FSMContext):
    if not callback.from_user.id in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.set_state(MailingConstructor.waiting_for_title)
    await callback.message.answer(
        "📝 <b>Создание новой рассылки</b>\n\n"
        "Введите название рассылки:",
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
        
    await state.update_data(title=message.text)
    await state.set_state(MailingConstructor.waiting_for_text)
    
    await message.answer(
        "📄 Введите текст рассылки. Можно использовать HTML разметку:",
        reply_markup=get_back_keyboard("admin_mailings")
    )

# Получение текста
@router.message(MailingConstructor.waiting_for_text)
async def mailing_get_text(message: Message, state: FSMContext):
    if not message.html_text and not message.text:
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
        await mailing_finalize(callback, state)
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
        await mailing_finalize(message, state)
    else:
        await message.answer(f"❌ Вы отправили неверный тип медиа. Ожидается: {media_type}")

# Финальный шаг - предпросмотр и сохранение
async def mailing_finalize(update, state: FSMContext):
    data = await state.get_data()
    
    # Создаем рассылку в БД
    mailing = db.create_mailing(
        title=data['title'],
        message_text=data['message_text'],
        message_type=data.get('message_type', 'text'),
        media_file_id=data.get('media_file_id'),
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

# Функция показа превью (вынесена для переиспользования)
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
    mailing_id = int(callback.data.replace("save_draft_", ""))
    db.change_mailing_status(mailing_id, "draft")
    await state.clear()
    
    await callback.answer("✅ Рассылка сохранена как черновик")
    # Используем answer вместо edit_text для избежания ошибок
    await callback.message.answer(
        "✅ Рассылка сохранена как черновик\n\n"
        "Вы можете найти её в разделе 'Черновики'",
        reply_markup=get_back_keyboard("admin_mailings")
    )

# Активация рассылки
@router.callback_query(F.data.startswith("activate_mailing_"))
async def activate_mailing(callback: CallbackQuery, state: FSMContext):
    mailing_id = int(callback.data.replace("activate_mailing_", ""))
    db.change_mailing_status(mailing_id, "active")
    await state.clear()
    
    await callback.answer("✅ Рассылка активирована")
    # Используем answer вместо edit_text для избежания ошибок
    await callback.message.answer(
        "✅ Рассылка активирована и готова к отправке\n\n"
        "Теперь вы можете отправить её через раздел 'Отправить рассылку'",
        reply_markup=get_back_keyboard("admin_mailings")
    )

# Отправка рассылки сразу
@router.callback_query(F.data.startswith("send_now_"))
async def send_mailing_now(callback: CallbackQuery, state: FSMContext, bot: Bot):
    mailing_id = int(callback.data.replace("send_now_", ""))
    await state.clear()
    
    from services.mailing import MailingService
    mailing_service = MailingService(bot)
    
    # Используем answer вместо edit_text для избежания ошибок
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

# Просмотр конкретной рассылки
@router.callback_query(F.data.startswith("view_mailing_"))
async def view_mailing(callback: CallbackQuery):
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

# Редактирование названия рассылки
@router.callback_query(F.data.startswith("edit_mailing_"))
async def edit_mailing_start(callback: CallbackQuery, state: FSMContext):
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

# Получение нового названия
@router.message(MailingConstructor.editing_title)
async def edit_mailing_title(message: Message, state: FSMContext):
    if len(message.text) > 200:
        await message.answer("❌ Слишком длинное название. Максимум 200 символов.")
        return
    
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    
    db.update_mailing(mailing_id, title=message.text)
    await state.set_state(MailingConstructor.editing_text)
    
    mailing = db.get_mailing(mailing_id)
    
    await message.answer(
        f"✅ Название обновлено!\n\n"
        f"Текущий текст: <b>{mailing['message_text'][:100]}...</b>\n\n"
        f"Введите новый текст рассылки:",
        parse_mode="HTML",
        reply_markup=get_back_keyboard(f"view_mailing_{mailing_id}")
    )

# Получение нового текста
@router.message(MailingConstructor.editing_text)
async def edit_mailing_text(message: Message, state: FSMContext):
    if not message.html_text and not message.text:
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
        await edit_mailing_finalize(callback, state)
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
        await edit_mailing_finalize(message, state)
    else:
        await message.answer(f"❌ Вы отправили неверный тип медиа. Ожидается: {media_type}")

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
    mailing_id = int(callback.data.replace("archive_mailing_", ""))
    db.change_mailing_status(mailing_id, "archived")
    
    await callback.answer("✅ Рассылка перемещена в архив")
    await callback.message.answer(
        "✅ Рассылка перемещена в архив",
        reply_markup=get_back_keyboard("admin_mailings")
    )

# Удаление рассылки
@router.callback_query(F.data.startswith("delete_mailing_"))
async def delete_mailing(callback: CallbackQuery):
    mailing_id = int(callback.data.replace("delete_mailing_", ""))
    db.change_mailing_status(mailing_id, "deleted")
    
    await callback.answer("✅ Рассылка удалена")
    await callback.message.answer(
        "✅ Рассылка удалена",
        reply_markup=get_back_keyboard("admin_mailings")
    )

# Выход из конструктора
@router.callback_query(F.data == "admin_mailings")
async def exit_constructor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from utils.helpers import get_mailings_keyboard
    await callback.message.answer(
        "📨 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_mailings_keyboard(),
        parse_mode="HTML"
    )

# Пропуск редактирования медиа
@router.callback_query(F.data.startswith("skip_edit_"))
async def skip_edit_media(callback: CallbackQuery, state: FSMContext):
    mailing_id = int(callback.data.replace("skip_edit_", ""))
    await edit_mailing_finalize(callback, state)
    await callback.answer("✅ Изменения сохранены")