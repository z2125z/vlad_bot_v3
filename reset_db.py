import os
from services.database import Base, db

def reset_database():
    """Сброс базы данных"""
    db_path = "bot.db"  # или ваш путь к БД
    
    # Закрываем соединение
    db.session.close()
    db.engine.dispose()
    
    # Удаляем файл базы данных если существует
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️ База данных {db_path} удалена")
    
    # Пересоздаем таблицы
    Base.metadata.create_all(db.engine)
    print("✅ База данных пересоздана")

if __name__ == "__main__":
    reset_database()