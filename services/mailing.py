from aiogram import Bot
from aiogram.types import Message, InputFile, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
import asyncio
import config
from services.logger import logger
from services.database import db
from utils.timezone import get_moscow_time, moscow_to_utc
from typing import Optional, Dict, Any, Tuple
from services.media_storage import media_storage

class MailingService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.semaphore = asyncio.Semaphore(20)  # Ограничение параллельных отправок
        # Устанавливаем бота в хранилище медиа
        media_storage.set_bot(bot)

    def _create_keyboard(self, buttons):
        """Создание клавиатуры из кнопок рассылки"""
        if not buttons:
            return None
            
        try:
            keyboard = InlineKeyboardBuilder()
            for button in buttons:
                if isinstance(button, dict):
                    if button.get('url'):
                        keyboard.add(InlineKeyboardButton(
                            text=button['text'], 
                            url=button['url']
                        ))
                    elif button.get('callback_data'):
                        keyboard.add(InlineKeyboardButton(
                            text=button['text'],
                            callback_data=button['callback_data']
                        ))
            return keyboard.as_markup()
        except Exception as e:
            logger.error(f"Error creating keyboard: {e}")
            return None

    async def _send_with_rate_limit(self, coroutine):
        """Отправка с ограничением скорости"""
        async with self.semaphore:
            try:
                return await coroutine
            except TelegramRetryAfter as e:
                logger.warning(f"Rate limit hit, waiting {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
                return await coroutine
            except Exception as e:
                raise e

    async def _send_media_with_local_storage(self, mailing: Dict[str, Any], user_id: int, keyboard):
        """Отправка медиа с использованием локального хранилища"""
        try:
            message = None
            
            if mailing['message_type'] == "text":
                message = await self.bot.send_message(
                    chat_id=user_id,
                    text=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            elif mailing['message_type'] == "photo":
                # Используем локальное хранилище
                photo_file = await media_storage.get_file_input(
                    mailing['media_file_id'], 
                    'photo'
                )
                message = await self.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_file,
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            elif mailing['message_type'] == "video":
                video_file = await media_storage.get_file_input(
                    mailing['media_file_id'], 
                    'video'
                )
                message = await self.bot.send_video(
                    chat_id=user_id,
                    video=video_file,
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            elif mailing['message_type'] == "document":
                # Для документов сохраняем оригинальное имя файла
                document_file = await media_storage.get_file_input(
                    mailing['media_file_id'], 
                    'document'
                )
                message = await self.bot.send_document(
                    chat_id=user_id,
                    document=document_file,
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            elif mailing['message_type'] == "voice":
                voice_file = await media_storage.get_file_input(
                    mailing['media_file_id'], 
                    'voice'
                )
                message = await self.bot.send_voice(
                    chat_id=user_id,
                    voice=voice_file,
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
            elif mailing['message_type'] == "video_note":
                video_note_file = await media_storage.get_file_input(
                    mailing['media_file_id'], 
                    'video_note'
                )
                message = await self.bot.send_video_note(
                    chat_id=user_id,
                    video_note=video_note_file
                )
                # Отправляем текст отдельно, если он есть
                if mailing['message_text'] and mailing['message_text'].strip():
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            
            return message
            
        except Exception as e:
            logger.error(f"Error sending media with local storage: {e}")
            raise

    async def send_mailing(self, mailing_id: int, user_id: int, target_group: str) -> Tuple[bool, Optional[int]]:
        """Отправка конкретной рассылки конкретному пользователю"""
        try:
            mailing = db.get_mailing(mailing_id)
            if not mailing:
                logger.error(f"Mailing {mailing_id} not found for user {user_id}")
                return False, None

            # Создаем запись статистики
            stats = db.add_mailing_stats(mailing_id, user_id, target_group)
            if not stats:
                logger.error(f"Failed to create stats for mailing {mailing_id}, user {user_id}")
                return False, None

            keyboard = self._create_keyboard(mailing['buttons'])

            try:
                message = await self._send_media_with_local_storage(mailing, user_id, keyboard)

                # Обновляем статистику
                if message:
                    db.update_mailing_stats(stats.id, 
                        sent=True, 
                        delivered=True,
                        delivered_at=moscow_to_utc(get_moscow_time())
                    )
                    
                    # Обновляем активность пользователя
                    db.update_user_activity(user_id)
                    
                    logger.info(f"Successfully sent mailing {mailing_id} to user {user_id}")
                    return True, message.message_id
                else:
                    db.update_mailing_stats(stats.id, sent=True, delivered=False)
                    logger.warning(f"Failed to send mailing {mailing_id} to user {user_id}")
                    return False, None
                
            except TelegramForbiddenError:
                # Пользователь заблокировал бота
                logger.warning(f"User {user_id} blocked the bot")
                db.update_mailing_stats(stats.id, sent=True, delivered=False)
                return False, None
            except TelegramBadRequest as e:
                # Другие ошибки Telegram
                logger.error(f"Telegram error sending to {user_id}: {e}")
                db.update_mailing_stats(stats.id, sent=True, delivered=False)
                return False, None
            except Exception as e:
                # Общие ошибки
                logger.error(f"Error sending to {user_id}: {e}", exc_info=True)
                db.update_mailing_stats(stats.id, sent=True, delivered=False)
                return False, None
                
        except Exception as e:
            logger.error(f"Critical error in send_mailing: {e}", exc_info=True)
            return False, None

    async def send_mailing_to_user(self, mailing_data: Dict[str, Any], user_id: int) -> Tuple[bool, Optional[int]]:
        """Отправка рассылки конкретному пользователю по данным"""
        try:
            keyboard = self._create_keyboard(mailing_data.get('buttons', []))
            message = await self._send_media_with_local_storage(mailing_data, user_id, keyboard)
            
            if message:
                db.update_user_activity(user_id)
                return True, message.message_id
            return False, None
            
        except Exception as e:
            logger.error(f"Error sending mailing to user {user_id}: {e}")
            return False, None

    async def send_trigger_mailing(self, user_id: int, trigger_word: str) -> Tuple[bool, Optional[int]]:
        """Отправка рассылки по кодовому слову"""
        try:
            mailing = db.get_mailing_by_trigger_word(trigger_word)
            if not mailing:
                return False, None

            # Создаем запись статистики
            stats = db.add_mailing_stats(mailing['id'], user_id, "trigger")
            if not stats:
                return False, None

            keyboard = self._create_keyboard(mailing['buttons'])

            try:
                message = await self._send_media_with_local_storage(mailing, user_id, keyboard)

                # Обновляем статистику
                if message:
                    db.update_mailing_stats(stats.id, 
                        sent=True, 
                        delivered=True,
                        delivered_at=moscow_to_utc(get_moscow_time())
                    )
                    db.update_user_activity(user_id)
                    return True, message.message_id
                else:
                    db.update_mailing_stats(stats.id, sent=True, delivered=False)
                    return False, None
                
            except Exception as e:
                db.update_mailing_stats(stats.id, sent=True, delivered=False)
                logger.error(f"Error sending trigger mailing to {user_id}: {e}")
                return False, None
                
        except Exception as e:
            logger.error(f"Critical error in send_trigger_mailing: {e}", exc_info=True)
            return False, None

    async def broadcast_mailing(self, mailing_id: int, target_group: str = "all") -> Tuple[bool, int, int]:
        """Массовая рассылка по выбранной группе пользователей"""
        try:
            mailing = db.get_mailing(mailing_id)
            if not mailing or mailing['status'] != "active":
                logger.error(f"Cannot send mailing {mailing_id} - not found or not active")
                return False, 0, 0

            # Предварительно скачиваем медиафайл (если есть) для ускорения рассылки
            if mailing['media_file_id']:
                try:
                    await media_storage.download_and_store(
                        mailing['media_file_id'], 
                        mailing['message_type']
                    )
                    logger.info(f"Pre-downloaded media for mailing {mailing_id}")
                except Exception as e:
                    logger.warning(f"Could not pre-download media for mailing {mailing_id}: {e}")

            # Выбираем пользователей в зависимости от целевой группы
            users = []
            target_name = ""
            
            if target_group == "all":
                users = db.get_all_users()
                target_name = "все пользователи"
            elif target_group == "active":
                users = db.get_active_users_today()
                target_name = "активные сегодня"
            elif target_group == "new_week":
                users = db.get_new_users_week()
                target_name = "новые пользователи (7 дней)"
            elif target_group == "new_month":
                users = db.get_new_users_month()
                target_name = "новые пользователи (30 дней)"
            else:
                users = db.get_all_users()
                target_name = "все пользователи"

            if not users:
                logger.warning(f"No users found for target group '{target_group}'")
                return True, 0, 0  # Возвращаем True т.к. это не ошибка, а отсутствие пользователей

            success_count = 0
            total_count = len(users)
            errors = []
            
            # Логируем начало рассылки
            logger.log_mailing_start(mailing_id, mailing['title'], target_group, total_count)
            
            # Статус начала рассылки для админа (только для массовых рассылок)
            progress_message = None
            if target_group != "trigger" and config.ADMIN_IDS:
                try:
                    progress_message = await self.bot.send_message(
                        chat_id=config.ADMIN_IDS[0],  # Первому админу
                        text=f"🔄 <b>Начинаю рассылку</b>\n\n"
                             f"📨 <b>Рассылка:</b> {mailing['title']}\n"
                             f"🎯 <b>Целевая группа:</b> {target_name}\n"
                             f"👥 <b>Получателей:</b> {total_count}\n"
                             f"📊 <b>Прогресс:</b> 0/{total_count} (0%)\n"
                             f"✅ <b>Успешно:</b> 0\n"
                             f"❌ <b>Ошибки:</b> 0",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to send progress message: {e}")

            for index, user in enumerate(users):
                success, _ = await self.send_mailing(
                    mailing_id=mailing_id,
                    user_id=user.user_id,
                    target_group=target_group
                )
                
                if success:
                    success_count += 1
                else:
                    errors.append(user.user_id)
                
                # Логируем прогресс каждые 10 сообщений
                if (index + 1) % 10 == 0:
                    logger.log_mailing_progress(mailing_id, index + 1, total_count, success_count)
                
                # Обновляем прогресс каждые 10 сообщений или каждые 10%
                if progress_message and ((index + 1) % 10 == 0 or index == total_count - 1):
                    progress = (index + 1) / total_count * 100
                    error_count = len(errors)
                    
                    try:
                        await progress_message.edit_text(
                            f"🔄 <b>Рассылка в процессе...</b>\n\n"
                            f"📨 <b>Рассылка:</b> {mailing['title']}\n"
                            f"🎯 <b>Целевая группа:</b> {target_name}\n"
                            f"👥 <b>Получателей:</b> {total_count}\n"
                            f"📊 <b>Прогресс:</b> {index + 1}/{total_count} ({progress:.1f}%)\n"
                            f"✅ <b>Успешно:</b> {success_count}\n"
                            f"❌ <b>Ошибки:</b> {error_count}",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Error updating progress: {e}")
                
                # Задержка чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.05)  # 20 сообщений в секунду
            
            # Логируем завершение рассылки
            logger.log_mailing_complete(mailing_id, success_count, total_count, len(errors))
            
            # Финальный статус
            if progress_message:
                success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                
                final_message = (
                    f"✅ <b>Рассылка завершена!</b>\n\n"
                    f"📨 <b>Рассылка:</b> {mailing['title']}\n"
                    f"🎯 <b>Целевая группа:</b> {target_name}\n"
                    f"👥 <b>Всего получателей:</b> {total_count}\n"
                    f"✅ <b>Успешно отправлено:</b> {success_count}\n"
                    f"❌ <b>Ошибок:</b> {len(errors)}\n"
                    f"📊 <b>Эффективность:</b> {success_rate:.1f}%"
                )
                
                if errors:
                    final_message += f"\n\n⚠️ <b>Не удалось отправить:</b> {len(errors)} пользователей"
                
                try:
                    await progress_message.edit_text(final_message, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Error sending final message: {e}")
            
            return True, success_count, total_count
            
        except Exception as e:
            logger.error(f"Critical error in broadcast_mailing: {e}", exc_info=True)
            return False, 0, 0