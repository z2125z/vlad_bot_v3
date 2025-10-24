from aiogram import Router, F
from aiogram.types import Message
from services.database import db

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user = db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    await message.answer(
        "👋 Добро пожаловать! Этот бот предназначен для рассылки уведомлений."
    )

@router.message()
async def all_messages(message: Message):
    # Обновляем активность пользователя
    db.update_user_activity(message.from_user.id)