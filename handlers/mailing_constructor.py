from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.database import db
from utils.helpers import get_mailing_type_keyboard, get_back_keyboard, format_mailing_preview, get_mailing_preview_keyboard
import config

router = Router()

class MailingConstructor(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_confirmation = State()

# Начало создания рассылки
@router.callback_query(F.data == "create_mailing")
async def create_mailing_start(callback: CallbackQuery, state: FSMContext):
    if not callback.from_user.id in config.ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.set_state(MailingConstructor.waiting_for_title)
    await callback.message.answer(  # Используем answer вместо edit_text
        "📝 <b>Создание новой рассылки</b>\n\n"
        "Введите название рассылки:",
        reply_markup=get_back_keyboard("admin_mailings"),
        parse_mode="HTML"
    )

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
    
    # Проверяем соответствие выбранного типа и отправленного контента
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

# Пропуск медиа (если передумали) - обработка кнопки "Назад"
@router.callback_query(MailingConstructor.waiting_for_media, F.data == "admin_mailings")
async def mailing_back_from_media(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from utils.helpers import get_mailings_keyboard
    await callback.message.edit_text(
        "📨 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_mailings_keyboard(),
        parse_mode="HTML"
    )

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
    
    await state.update_data(mailing_id=mailing.id)
    await state.set_state(MailingConstructor.waiting_for_confirmation)
    
    preview_text = format_mailing_preview(mailing)
    
    # Отправляем превью
    if update.__class__.__name__ == "CallbackQuery":
        message = update.message
        send_method = message.edit_text
    else:
        message = update
        send_method = message.answer
    
    try:
        if mailing.message_type == "text":
            await send_method(
                preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
        elif mailing.message_type == "photo":
            await message.answer_photo(
                mailing.media_file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
        elif mailing.message_type == "video":
            await message.answer_video(
                mailing.media_file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
        elif mailing.message_type == "document":
            await message.answer_document(
                mailing.media_file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
        elif mailing.message_type == "voice":
            await message.answer_voice(
                mailing.media_file_id,
                caption=preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
        elif mailing.message_type == "video_note":
            await message.answer_video_note(
                mailing.media_file_id
            )
            await message.answer(
                preview_text,
                parse_mode="HTML",
                reply_markup=get_mailing_preview_keyboard(mailing.id)
            )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка отображения превью: {e}\n\n"
            f"📝 Текст рассылки: {mailing.message_text[:500]}...",
            reply_markup=get_mailing_preview_keyboard(mailing.id)
        )

# Сохранение как черновика
@router.callback_query(F.data.startswith("save_draft_"))
async def save_mailing_draft(callback: CallbackQuery, state: FSMContext):
    mailing_id = int(callback.data.replace("save_draft_", ""))
    db.change_mailing_status(mailing_id, "draft")
    await state.clear()
    
    await callback.answer("✅ Рассылка сохранена как черновик")
    await callback.message.edit_text(
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
    await callback.message.edit_text(
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
    
    await callback.message.edit_text("🔄 Подготовка к отправке...")
    
    # Отправляем всем пользователям
    success, success_count, total_count = await mailing_service.broadcast_mailing(
        mailing_id=mailing_id,
        target_group="all"
    )
    
    if success:
        await callback.message.edit_text(
            f"✅ <b>Рассылка отправлена!</b>\n\n"
            f"📤 Отправлено: {success_count}/{total_count} сообщений\n"
            f"📊 Успешных: {(success_count/total_count*100 if total_count > 0 else 0):.1f}%\n\n"
            f"Статистику можно посмотреть в разделе 'Статистика рассылок'",
            parse_mode="HTML",
            reply_markup=get_back_keyboard("admin_mailings")
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при отправке рассылки",
            reply_markup=get_back_keyboard("admin_mailings")
        )

# Выход из конструктора
@router.callback_query(MailingConstructor.waiting_for_confirmation, F.data == "admin_mailings")
async def exit_constructor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from utils.helpers import get_mailings_keyboard
    await callback.message.edit_text(
        "📨 <b>Управление рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_mailings_keyboard(),
        parse_mode="HTML"
    )