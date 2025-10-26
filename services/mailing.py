from aiogram import Bot
from aiogram.types import Message, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from services.database import db
from datetime import datetime, timedelta
import asyncio
import config

class MailingService:
    def __init__(self, bot: Bot):
        self.bot = bot

    def _create_keyboard(self, buttons):
        if not buttons:
            return None
            
        keyboard = InlineKeyboardBuilder()
        for button in buttons:
            if button.get('url'):
                keyboard.add(InlineKeyboardButton(
                    text=button['text'], 
                    url=button['url']
                ))
        return keyboard.as_markup()

    async def send_mailing(self, mailing_id: int, user_id: int, target_group: str):
        mailing = db.get_mailing(mailing_id)
        if not mailing:
            return False, None

        # Создаем запись статистики
        stats = db.add_mailing_stats(mailing_id, user_id, target_group)
        keyboard = self._create_keyboard(mailing['buttons'])

        try:
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
                message = await self.bot.send_video_note(
                    chat_id=user_id,
                    video_note=mailing['media_file_id']
                )
                # Для видео-сообщений отправляем текст отдельно
                if mailing['message_text']:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            
            # Обновляем статистику
            db.update_mailing_stats(stats.id, 
                sent=True, 
                delivered=True,
                delivered_at=datetime.utcnow()
            )
            
            return True, message.message_id
            
        except TelegramForbiddenError as e:
            # Пользователь заблокировал бота
            print(f"User {user_id} blocked the bot")
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None
        except TelegramBadRequest as e:
            # Другие ошибки Telegram
            print(f"Failed to send to {user_id}: {e}")
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None
        except Exception as e:
            # Общие ошибки
            print(f"Error sending to {user_id}: {e}")
            db.update_mailing_stats(stats.id, sent=True, delivered=False)
            return False, None

    async def broadcast_mailing(self, mailing_id: int, target_group: str = "all"):
        mailing = db.get_mailing(mailing_id)
        if not mailing or mailing['status'] != "active":
            return False, 0, 0

        # Выбираем пользователей в зависимости от целевой группы
        if target_group == "all":
            users = db.get_all_users()
            target_name = "все пользователи"
        elif target_group == "active":
            users = db.get_active_users_today()
            target_name = "активные сегодня"
        elif target_group == "new":
            users = db.get_new_users(days=7)  # Новые за последние 7 дней
            target_name = "новые пользователи"
        else:
            users = db.get_all_users()
            target_name = "все пользователи"

        if not users:
            return False, 0, 0

        success_count = 0
        total_count = len(users)
        
        # Статус начала рассылки
        progress_message = await self.bot.send_message(
            chat_id=config.ADMIN_IDS[0],  # Первому админу
            text=f"🔄 Начинаю рассылку...\n"
                 f"📨 Рассылка: {mailing['title']}\n"
                 f"🎯 Целевая группа: {target_name}\n"
                 f"👥 Получателей: {total_count}\n"
                 f"📊 Прогресс: 0/{total_count} (0%)"
        )
        
        for index, user in enumerate(users):
            success, _ = await self.send_mailing(
                mailing_id=mailing_id,
                user_id=user.user_id,
                target_group=target_group
            )
            
            if success:
                success_count += 1
            
            # Обновляем прогресс каждые 10 сообщений или каждые 10%
            if (index + 1) % 10 == 0 or index == total_count - 1:
                progress = (index + 1) / total_count * 100
                try:
                    await progress_message.edit_text(
                        f"🔄 Рассылка в процессе...\n"
                        f"📨 Рассылка: {mailing['title']}\n"
                        f"🎯 Целевая группа: {target_name}\n"
                        f"👥 Получателей: {total_count}\n"
                        f"📊 Прогресс: {index + 1}/{total_count} ({progress:.1f}%)\n"
                        f"✅ Успешно: {success_count}"
                    )
                except:
                    pass
            
            # Задержка чтобы не превысить лимиты Telegram (30 сообщений в секунду)
            await asyncio.sleep(0.05)  # 20 сообщений в секунду
        
        # Финальный статус
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        try:
            await progress_message.edit_text(
                f"✅ <b>Рассылка завершена!</b>\n\n"
                f"📨 Рассылка: {mailing['title']}\n"
                f"🎯 Целевая группа: {target_name}\n"
                f"👥 Всего получателей: {total_count}\n"
                f"✅ Успешно отправлено: {success_count}\n"
                f"📊 Эффективность: {success_rate:.1f}%",
                parse_mode="HTML"
            )
        except:
            pass
        
        return True, success_count, total_count