from services.database import db, Base, WelcomeMessage, Mailing
from sqlalchemy import text, inspect

def run_migration():
    """Запуск миграции для добавления новых таблиц и полей"""
    try:
        # Создаем таблицу welcome_messages если не существует
        inspector = inspect(db.engine)
        if not inspector.has_table('welcome_messages'):
            WelcomeMessage.__table__.create(db.engine)
            print("✅ Таблица welcome_messages создана")
        
        # Добавляем новые поля в таблицу mailings если их нет
        existing_columns = [col['name'] for col in inspector.get_columns('mailings')]
        
        if 'trigger_word' not in existing_columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE mailings ADD COLUMN trigger_word VARCHAR(100)"))
                conn.commit()
                print("✅ Колонка trigger_word добавлена")
                
        if 'is_trigger_mailing' not in existing_columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE mailings ADD COLUMN is_trigger_mailing BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("✅ Колонка is_trigger_mailing добавлена")
        
        print("✅ Миграция завершена успешно")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_migration()