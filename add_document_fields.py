from services.database import db, Base
from sqlalchemy import inspect, text

def add_document_fields():
    """Добавить поля для хранения информации о документах"""
    try:
        print("🔄 Добавление полей для документов...")
        
        inspector = inspect(db.engine)
        
        # Проверяем таблицу mailings
        if inspector.has_table('mailings'):
            existing_columns = [col['name'] for col in inspector.get_columns('mailings')]
            
            # Добавляем document_original_name если нет
            if 'document_original_name' not in existing_columns:
                try:
                    with db.engine.connect() as conn:
                        if db.engine.url.drivername == 'sqlite':
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_original_name VARCHAR(255)"))
                        else:
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_original_name VARCHAR(255)"))
                        print("✅ Колонка document_original_name добавлена")
                except Exception as e:
                    print(f"⚠️ Не удалось добавить document_original_name: {e}")
            
            # Добавляем document_mime_type если нет
            if 'document_mime_type' not in existing_columns:
                try:
                    with db.engine.connect() as conn:
                        if db.engine.url.drivername == 'sqlite':
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_mime_type VARCHAR(100)"))
                        else:
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_mime_type VARCHAR(100)"))
                        print("✅ Колонка document_mime_type добавлена")
                except Exception as e:
                    print(f"⚠️ Не удалось добавить document_mime_type: {e}")
            
            # Добавляем document_file_size если нет
            if 'document_file_size' not in existing_columns:
                try:
                    with db.engine.connect() as conn:
                        if db.engine.url.drivername == 'sqlite':
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_file_size INTEGER"))
                        else:
                            conn.execute(text("ALTER TABLE mailings ADD COLUMN document_file_size INTEGER"))
                        print("✅ Колонка document_file_size добавлена")
                except Exception as e:
                    print(f"⚠️ Не удалось добавить document_file_size: {e}")
        
        print("🎉 Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_document_fields()