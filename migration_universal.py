from services.database import db, Base
from sqlalchemy import inspect, text

def run_universal_migration():
    """Универсальная миграция для любой базы данных"""
    try:
        print("🔄 Запуск универсальной миграции...")
        
        # Создаем все таблицы
        Base.metadata.create_all(db.engine)
        print("✅ Все таблицы созданы/проверены")
        
        # Получаем инспектор для проверки структуры БД
        inspector = inspect(db.engine)
        
        # Проверяем и добавляем недостающие колонки
        with db.engine.connect() as conn:
            # Проверяем таблицу mailings
            if inspector.has_table('mailings'):
                existing_columns = [col['name'] for col in inspector.get_columns('mailings')]
                
                # Добавляем trigger_word если нет
                if 'trigger_word' not in existing_columns:
                    try:
                        if db.engine.url.drivername == 'sqlite':
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN trigger_word TEXT"))
                        else:
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN trigger_word VARCHAR(100)"))
                        print("✅ Колонка trigger_word добавлена")
                    except Exception as e:
                        print(f"⚠️ Не удалось добавить trigger_word: {e}")
                
                # Добавляем is_trigger_mailing если нет
                if 'is_trigger_mailing' not in existing_columns:
                    try:
                        if db.engine.url.drivername == 'sqlite':
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN is_trigger_mailing BOOLEAN DEFAULT 0"))
                        else:
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN is_trigger_mailing BOOLEAN DEFAULT FALSE"))
                        print("✅ Колонка is_trigger_mailing добавлена")
                    except Exception as e:
                        print(f"⚠️ Не удалось добавить is_trigger_mailing: {e}")
            
            conn.commit()
        
        print("🎉 Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_universal_migration()