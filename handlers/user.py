from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from services.database import db
from services.mailing import MailingService
from aiogram import Bot
from services.logger import logger

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
    """Обработка команды /start"""
    try:
        # Добавляем/обновляем пользователя
        user = db.add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        
        if not user:
            await message.answer("❌ Произошла ошибка при регистрации. Попробуйте позже.")
            return
        
        # Обновляем активность
        db.update_user_activity(message.from_user.id)
        
        # Отправляем приветственное сообщение
        welcome = db.get_welcome_message()
        if welcome:
            mailing_service = MailingService(bot)
            
            # Создаем временную рассылку для отправки приветствия
            temp_mailing = {
                'id': 0,
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
                await send_default_welcome(message)
        else:
            await send_default_welcome(message)
            
        logger.log_user_activity(message.from_user.id, "started bot")
        
    except Exception as e:
        logger.error(f"Error in cmd_start for user {message.from_user.id}: {e}", exc_info=True)
        await send_default_welcome(message)

async def send_default_welcome(message: Message):
    """Отправка стандартного приветственного сообщения"""
    # Получаем список активных кодовых слов
    trigger_mailings = db.get_active_trigger_mailings()
    
    welcome_text = "👋 Добро пожаловать! Этот бот предназначен для рассылки уведомлений.\n\n"
    welcome_text += "💡 <b>Доступные команды:</b>\n"
    welcome_text += "/start - начать работу\n"
    welcome_text += "/help - помощь\n\n"
    
    if trigger_mailings:
        welcome_text += "🔤 <b>Кодовые слова:</b>\n"
        welcome_text += "Введите одно из слов чтобы получить информацию:\n"
        for mailing in trigger_mailings:
            if mailing.get('trigger_word'):
                welcome_text += f"• <code>{mailing['trigger_word']}</code> - {mailing['title']}\n"
    else:
        welcome_text += "🔤 <b>Примеры кодовых слов:</b>\n"
        welcome_text += "• <code>прайс</code> - наши цены\n"
        welcome_text += "• <code>услуги</code> - список услуг\n"
        welcome_text += "• <code>контакты</code> - контактная информация\n"
    
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда помощи с списком кодовых слов"""
    try:
        trigger_mailings = db.get_active_trigger_mailings()
        
        help_text = "💡 <b>Помощь по боту</b>\n\n"
        help_text += "🔤 <b>Доступные кодовые слова:</b>\n"
        
        if trigger_mailings:
            for mailing in trigger_mailings:
                if mailing.get('trigger_word'):
                    # УБИРАЕМ ИНФОРМАЦИЮ О КОЛИЧЕСТВЕ ОТПРАВЛЕННЫХ РАССЫЛОК
                    help_text += f"• <code>{mailing['trigger_word']}</code> - {mailing['title']}\n"
        else:
            help_text += "• <code>прайс</code> - наши цены\n"
            help_text += "• <code>услуги</code> - список услуг\n"
            help_text += "• <code>контакты</code> - контактная информация\n"
        
        help_text += "\n📝 <b>Как использовать:</b>\n"
        help_text += "Просто введите любое кодовое слово из списка выше, и бот отправит вам соответствующую информацию."
        
        await message.answer(help_text, parse_mode="HTML")
        db.update_user_activity(message.from_user.id)
        
    except Exception as e:
        logger.error(f"Error in cmd_help for user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при загрузке помощи. Попробуйте позже.")

@router.message()
async def all_messages(message: Message, bot: Bot):
    """Обработка всех сообщений (кодовые слова)"""
    try:
        # Пропускаем команды
        if message.text and message.text.startswith('/'):
            return
        
        # Обновляем активность пользователя
        db.update_user_activity(message.from_user.id)
        
        if message.text:
            trigger_word = message.text.strip().lower()
            
            # Ищем рассылку по кодовому слову
            mailing = db.get_mailing_by_trigger_word(trigger_word)
            
            if mailing:
                mailing_service = MailingService(bot)
                success, _ = await mailing_service.send_trigger_mailing(
                    user_id=message.from_user.id,
                    trigger_word=trigger_word
                )
                
                # УБИРАЕМ СООБЩЕНИЕ "✅ Информация отправлена!"
                # Просто логируем успешную отправку
                if success:
                    logger.log_user_activity(message.from_user.id, f"triggered mailing: {trigger_word}")
                else:
                    # Оставляем сообщение об ошибке только если не удалось отправить
                    await message.answer("❌ Произошла ошибка при отправке информации")
            else:
                # Если слово не найдено, показываем подсказку
                await message.answer(
                    "❌ Неизвестное кодовое слово.\n\n"
                    "💡 Введите /help чтобы увидеть список доступных слов."
                )
                
    except Exception as e:
        logger.error(f"Error processing message from user {message.from_user.id}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке сообщения.")