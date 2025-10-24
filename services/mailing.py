from aiogram import Bot
from aiogram.types import Message, InputFile
from aiogram.exceptions import TelegramBadRequest
from services.database import db, MailingStats
from datetime import datetime
import asyncio

class MailingService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_mailing(self, mailing_id: int, user_id: int, message_text: str, 
                          message_type: str, file_id: str = None):
        try:
            if message_type == "text":
                message = await self.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="HTML"
                )
            elif message_type == "photo":
                message = await self.bot.send_photo(
                    chat_id=user_id,
                    photo=file_id,
                    caption=message_text,
                    parse_mode="HTML"
                )
            elif message_type == "document":
                message = await self.bot.send_document(
                    chat_id=user_id,
                    document=file_id,
                    caption=message_text,
                    parse_mode="HTML"
                )
            
            # Записываем статистику
            stats = MailingStats(
                mailing_id=mailing_id,
                user_id=user_id,
                delivered=True,
                delivered_at=datetime.utcnow()
            )
            db.session.add(stats)
            db.session.commit()
            
            return True, message.message_id
            
        except TelegramBadRequest as e:
            print(f"Failed to send to {user_id}: {e}")
            return False, None
        except Exception as e:
            print(f"Error sending to {user_id}: {e}")
            return False, None

    async def broadcast_mailing(self, mailing_id: int, users: list):
        mailing = db.session.query(db.Mailing).filter_by(id=mailing_id).first()
        if not mailing:
            return False

        success_count = 0
        total_count = len(users)
        
        for user in users:
            success, _ = await self.send_mailing(
                mailing_id=mailing_id,
                user_id=user.user_id,
                message_text=mailing.message_text,
                message_type=mailing.message_type,
                file_id=mailing.file_id
            )
            
            if success:
                success_count += 1
                mailing.sent_count = success_count
                db.session.commit()
            
            # Задержка чтобы не превысить лимиты Telegram
            await asyncio.sleep(0.1)
        
        return success_count, total_count