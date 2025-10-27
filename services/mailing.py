from aiogram import Bot
from aiogram.types import Message, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import asyncio
import config
from services.logger import logger

class MailingService:
    def __init__(self, bot: Bot):
        self.bot = bot

    def _create_keyboard(self, buttons):
        """Создание клавиатуры из кнопок рассылки"""
        if not buttons:
            return None
            
        keyboard = InlineKeyboardBuilder()
        for button in buttons:
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

    async def send_mailing(self, mailing_id: int, user_id: int, target_group: str):
        """Отправка конкретной рассылки конкретному пользователю"""
        from services.database import db
        from utils.timezone import get_moscow_time, moscow_to_utc
        
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
            message = None
            
            if mailing['message_type'] == "text":
                message = await self.bot.send_message(
                    chat_id=user_id,
                    text=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif mailing['message_type'] == "photo":
                message = await self.bot.send_photo(
                    chat_id=user_id,
                    photo=mailing['media_file_id'],
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif mailing['message_type'] == "video":
                message = await self.bot.send_video(
                    chat_id=user_id,
                    video=mailing['media_file_id'],
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif mailing['message_type'] == "document":
                message = await self.bot.send_document(
                    chat_id=user_id,
                    document=mailing['media_file_id'],
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif mailing['message_type'] == "voice":
                message = await self.bot.send_voice(
                    chat_id=user_id,
                    voice=mailing['media_file_id'],
                    caption=mailing['message_text'],
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            elif mailing['message_type'] == "video_note":
                # Для видео-сообщений сначала отправляем видео
                message = await self.bot.send_video_note(
                    chat_id=user_id,
                    video_note=mailing['media_file_id']
                )
                # Затем отправляем текст отдельно, если он есть
                if mailing['message_text']:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            
            # Обновляем статистику с московским временем
            if message:
                db.update_mailing_stats(stats.id, 
                    sent=True, 
                    delivered=True,
                    delivered_at=moscow_to_utc(get_moscow_time())
                )
                
                # ОБНОВЛЯЕМ АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЯ ПРИ УСПЕШНОЙ РАССЫЛКЕ
                db.update_user_activity(user_id)
                
                logger.info(f"Successfully sent mailing {mailing_id} to user {user_id}")
                return True, message.message_id
            else:
                db.update_mailing_stats(stats.id, sent=True, delivered=False)
                logger.warning(f"Failed to send mailing {mailing_id} to user {user_id} - no message returned")
                return False, None
            
        except TelegramForbiddenError as e:
            # Пользователь заблокировал бота
            logger.warning(f"User {user_id} blocked the bot: {e}")
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None
        except TelegramBadRequest as e:
            # Другие ошибки Telegram (неверный chat_id и т.д.)
            logger.error(f"Failed to send to {user_id}: {e}")
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None
        except Exception as e:
            # Общие ошибки
            logger.error(f"Error sending to {user_id}: {e}", exc_info=True)
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None

    async def broadcast_mailing(self, mailing_id: int, target_group: str = "all"):
        """Массовая рассылка по выбранной группе пользователей"""
        from services.database import db
        
        mailing = db.get_mailing(mailing_id)
        if not mailing or mailing['status'] != "active":
            logger.error(f"Cannot send mailing {mailing_id} - not found or not active")
            return False, 0, 0

        # Выбираем пользователей в зависимости от целевой группы
        if target_group == "all":
            users = db.get_all_users()
            target_name = "все пользователи"
        elif target_group == "active":
            users = db.get_active_users_today()
            target_name = "активные сегодня"
        elif target_group == "new_week":
            users = db.get_new_users_week()  # Новые за неделю
            target_name = "новые пользователи (7 дней)"
        elif target_group == "new_month":
            users = db.get_new_users_month()  # Новые за месяц
            target_name = "новые пользователи (30 дней)"
        else:
            users = db.get_all_users()
            target_name = "все пользователи"

        if not users:
            logger.warning(f"No users found for target group '{target_group}'")
            return False, 0, 0

        success_count = 0
        total_count = len(users)
        errors = []
        
        # Логируем начало рассылки
        logger.log_mailing_start(mailing_id, mailing['title'], target_group, total_count)
        
        # Статус начала рассылки для админа
        progress_message = None
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
            success, message_id = await self.send_mailing(
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
            if (index + 1) % 10 == 0 or index == total_count - 1:
                progress = (index + 1) / total_count * 100
                error_count = len(errors)
                
                try:
                    if progress_message:
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
            
            # Задержка чтобы не превысить лимиты Telegram (30 сообщений в секунду)
            await asyncio.sleep(0.05)  # 20 сообщений в секунду
        
        # Логируем завершение рассылки
        logger.log_mailing_complete(mailing_id, success_count, total_count, len(errors))
        
        # Финальный статус
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
            if progress_message:
                await progress_message.edit_text(final_message, parse_mode="HTML")
            else:
                # Если прогресс-сообщение не было создано, отправляем финальный результат
                await self.bot.send_message(
                    chat_id=config.ADMIN_IDS[0],
                    text=final_message,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Error sending final message: {e}")
        
        return True, success_count, total_count