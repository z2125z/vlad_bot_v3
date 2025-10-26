import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Настройки времени
TIMEZONE = "Europe/Moscow"