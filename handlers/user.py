from aiogram import Router, F
from aiogram.types import Message
from services.database import db
from services.mailing import MailingService
from aiogram import Bot

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message, bot: Bot):
    user = db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    # Отправляем приветственное сообщение
    welcome = db.get_welcome_message()
    if welcome:
        mailing_service = MailingService(bot)
        
        # Создаем временную рассылку для отправки приветствия
        temp_mailing = {
            'id': 0,  # Временный ID
            'message_text': welcome['message_text'],
            'message_type': welcome['message_type'],
            'media_file_id': welcome['media_file_id'],
            'buttons': []
        }
        
        # Используем логику отправки из MailingService
        success, _ = await mailing_service.send_mailing_to_user(
            mailing_data=temp_mailing,
            user_id=message.from_user.id
        )
        
        if not success:
            # Fallback: отправляем простой текст если не удалось отправить форматированное сообщение
            await message.answer(
                "👋 Добро пожаловать! Этот бот предназначен для рассылки уведомлений.\n\n"
                "💡 <b>Доступные команды:</b>\n"
                "/start - начать работу\n"
                "/help - помощь\n\n"
                "🔤 <b>Кодовые слова:</b>\n"
                "Введите одно из слов чтобы получить информацию:\n"
                "• <code>прайс</code> - наши цены\n"
                "• <code>услуги</code> - список услуг\n"
                "• <code>контакты</code> - контактная информация",
                parse_mode="HTML"
            )
    else:
        await message.answer(
            "👋 Добро пожаловать! Этот бот предназначен для рассылки уведомлений.\n\n"
            "💡 <b>Доступные команды:</b>\n"
            "/start - начать работу\n"
            "/help - помощь\n\n"
            "🔤 <b>Кодовые слова:</b>\n"
            "Введите одно из слов чтобы получить информацию:\n"
            "• <code>прайс</code> - наши цены\n"
            "• <code>услуги</code> - список услуг\n"
            "• <code>контакты</code> - контактная информация",
            parse_mode="HTML"
        )

@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Команда помощи с списком кодовых слов"""
    trigger_mailings = db.get_active_trigger_mailings()
    
    help_text = "💡 <b>Помощь по боту</b>\n\n"
    help_text += "🔤 <b>Доступные кодовые слова:</b>\n"
    
    if trigger_mailings:
        for mailing in trigger_mailings:
            if mailing.get('trigger_word'):
                help_text += f"• <code>{mailing['trigger_word']}</code> - {mailing['title']}\n"
    else:
        help_text += "• <code>прайс</code> - наши цены\n"
        help_text += "• <code>услуги</code> - список услуг\n"
        help_text += "• <code>контакты</code> - контактная информация\n"
    
    help_text += "\n📝 <b>Как использовать:</b>\n"
    help_text += "Просто введите любое кодовое слово из списка выше, и бот отправит вам соответствующую информацию."
    
    await message.answer(help_text, parse_mode="HTML")

@router.message()
async def all_messages(message: Message, bot: Bot):
    # Обновляем активность пользователя
    db.update_user_activity(message.from_user.id)
    
    # Пропускаем команды
    if message.text and message.text.startswith('/'):
        return
        
    # Обрабатываем кодовые слова
    if message.text:
        trigger_word = message.text.strip().lower()
        mailing = db.get_mailing_by_trigger_word(trigger_word)
        
        if mailing:
            mailing_service = MailingService(bot)
            success, _ = await mailing_service.send_mailing(
                mailing_id=mailing['id'],
                user_id=message.from_user.id,
                target_group="trigger"
            )
            
            if success:
                await message.answer("✅ Информация отправлена!")
            else:
                await message.answer("❌ Произошла ошибка при отправке информации")
        else:
            # Если слово не найдено, показываем подсказку
            await message.answer(
                "❌ Неизвестное кодовое слово.\n\n"
                "💡 Введите /help чтобы увидеть список доступных слов."
            )