from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index, cast
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import config
import json
import pytz
import logging
from typing import Optional, List, Dict, Any, Union

# Создаем локальный логгер для этого модуля
logger = logging.getLogger('database')

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)

    # Убираем ВСЕ индексы из __table_args__ - они уже созданы через index=True
    __table_args__ = ()

class WelcomeMessage(Base):
    __tablename__ = 'welcome_messages'
    
    id = Column(Integer, primary_key=True)
    message_text = Column(Text)
    message_type = Column(String(50), default='text')
    media_file_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Mailing(Base):
    __tablename__ = 'mailings'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    message_text = Column(Text)
    message_type = Column(String(50), nullable=False)
    media_file_id = Column(String(255), nullable=True)
    status = Column(String(50), default='draft', index=True)  # Индекс в колонке
    buttons = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)  # Индекс в колонке
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trigger_word = Column(String(100), nullable=True, index=True)  # Индекс в колонке
    is_trigger_mailing = Column(Boolean, default=False, index=True)  # Индекс в колонке
    # Новые поля для документов
    document_original_name = Column(String(255), nullable=True)
    document_mime_type = Column(String(100), nullable=True)
    document_file_size = Column(Integer, nullable=True)

    # Оставляем только составные или специальные индексы, которых нет в колонках
    __table_args__ = (
        # Создаем составные индексы или индексы по функциям если нужно
        # Для производительности можно добавить составные индексы
        Index('ix_mailings_status_type', 'status', 'message_type'),
        Index('ix_mailings_trigger_status', 'trigger_word', 'status'),
    )

class MailingStats(Base):
    __tablename__ = 'mailing_stats'
    
    id = Column(Integer, primary_key=True)
    mailing_id = Column(Integer, ForeignKey('mailings.id'), index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), index=True)
    target_group = Column(String(50))
    sent = Column(Boolean, default=False)
    delivered = Column(Boolean, default=False, index=True)  # Индекс в колонке
    read = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True, index=True)  # Индекс в колонке
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    mailing = relationship("Mailing", backref="stats")
    user = relationship("User")

    # Оставляем только составные индексы
    __table_args__ = (
        Index('ix_mailing_stats_mailing_user', 'mailing_id', 'user_id'),
        Index('ix_mailing_stats_mailing_sent', 'mailing_id', 'sent_at'),
    )


class Database:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
        self._setup_logger()
        self._create_tables()
        Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = Session
        self.log_info("Database initialized")

    def _setup_logger(self):
        """Настройка логгера для этого модуля"""
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    def log_info(self, message: str):
        """Логирование информационных сообщений"""
        logger.info(message)

    def log_error(self, message: str, exc_info: bool = False):
        """Логирование ошибок"""
        logger.error(message, exc_info=exc_info)

    def log_warning(self, message: str):
        """Логирование предупреждений"""
        logger.warning(message)

    def log_debug(self, message: str):
        """Логирование отладочной информации"""
        logger.debug(message)

    def _create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            Base.metadata.create_all(self.engine)
            self.log_info("Tables created/verified")
        except Exception as e:
            self.log_error(f"Error creating tables: {e}", exc_info=True)
            # Вместо падения, пытаемся удалить существующую БД и создать заново
            # Это крайняя мера для разработки
            if "already exists" in str(e):
                self.log_warning("Database has duplicate indexes. Consider dropping and recreating the database.")
            raise

    def get_session(self):
        """Получить новую сессию для работы с БД"""
        return self.Session()

    def get_current_utc_time(self):
        """Получить текущее время в UTC"""
        return datetime.utcnow()

    def _get_mailing_dict(self, mailing) -> Optional[Dict[str, Any]]:
        """Преобразует объект Mailing в словарь"""
        if not mailing:
            return None
            
        mailing_dict = {
            'id': mailing.id,
            'title': mailing.title,
            'message_text': mailing.message_text,
            'message_type': mailing.message_type,
            'media_file_id': mailing.media_file_id,
            'status': mailing.status,
            'trigger_word': mailing.trigger_word,
            'is_trigger_mailing': mailing.is_trigger_mailing,
            'document_original_name': mailing.document_original_name,
            'document_mime_type': mailing.document_mime_type,
            'document_file_size': mailing.document_file_size,
            'created_at': mailing.created_at,
            'updated_at': mailing.updated_at
        }
        
        # Безопасная обработка кнопок
        if mailing.buttons and mailing.buttons.strip():
            try:
                mailing_dict['buttons'] = json.loads(mailing.buttons)
            except (json.JSONDecodeError, TypeError) as e:
                self.log_warning(f"Error parsing buttons for mailing {mailing.id}: {e}")
                mailing_dict['buttons'] = []
        else:
            mailing_dict['buttons'] = []
            
        return mailing_dict

    # МЕТОДЫ ДЛЯ ПРИВЕТСТВЕННЫХ СООБЩЕНИЙ
    def get_welcome_message(self) -> Optional[Dict[str, Any]]:
        """Получить активное приветственное сообщение"""
        session = self.get_session()
        try:
            welcome = session.query(WelcomeMessage).filter_by(is_active=True).first()
            if welcome:
                return {
                    'id': welcome.id,
                    'message_text': welcome.message_text,
                    'message_type': welcome.message_type,
                    'media_file_id': welcome.media_file_id,
                    'is_active': welcome.is_active,
                    'created_at': welcome.created_at,
                    'updated_at': welcome.updated_at
                }
            return None
        except Exception as e:
            self.log_error(f"Error getting welcome message: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def update_welcome_message(self, message_text: str, message_type: str = "text", media_file_id: str = None) -> bool:
        """Обновить приветственное сообщение"""
        session = self.get_session()
        try:
            # Деактивируем все существующие
            session.query(WelcomeMessage).update({'is_active': False})
            
            # Создаем новое
            welcome = WelcomeMessage(
                message_text=message_text,
                message_type=message_type,
                media_file_id=media_file_id,
                is_active=True
            )
            session.add(welcome)
            session.commit()
            self.log_info("Welcome message updated")
            return True
        except Exception as e:
            self.log_error(f"Error updating welcome message: {e}", exc_info=True)
            session.rollback()
            return False
        finally:
            session.close()

    # МЕТОДЫ ДЛЯ РАССЫЛОК ПО ЗАПРОСУ
    def get_active_trigger_mailings(self) -> List[Dict[str, Any]]:
        """Получить все активные рассылки по запросу"""
        session = self.get_session()
        try:
            mailings = session.query(Mailing).filter(
                Mailing.is_trigger_mailing == True,
                Mailing.status == 'active'
            ).all()
            return [self._get_mailing_dict(mailing) for mailing in mailings if mailing]
        except Exception as e:
            self.log_error(f"Error getting active trigger mailings: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_mailing_by_trigger_word(self, trigger_word: str) -> Optional[Dict[str, Any]]:
        """Найти рассылку по кодовому слову"""
        if not trigger_word:
            return None
            
        session = self.get_session()
        try:
            mailing = session.query(Mailing).filter(
                Mailing.trigger_word == trigger_word,
                Mailing.is_trigger_mailing == True,
                Mailing.status == 'active'
            ).first()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            self.log_error(f"Error getting mailing by trigger word '{trigger_word}': {e}", exc_info=True)
            return None
        finally:
            session.close()

    # ОПТИМИЗИРОВАННЫЕ МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
    def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        session = self.get_session()
        try:
            return session.query(User).filter_by(user_id=user_id).first()
        except Exception as e:
            self.log_error(f"Error getting user {user_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def add_user(self, user_id: int, username: str, full_name: str) -> Optional[User]:
        """Добавить нового пользователя или обновить существующего"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                user = User(user_id=user_id, username=username, full_name=full_name)
                session.add(user)
                session.commit()
                self.log_info(f"New user added: {user_id} (@{username})")
            elif user.username != username or user.full_name != full_name:
                # Обновляем информацию если изменилась
                user.username = username
                user.full_name = full_name
                session.commit()
                self.log_info(f"User info updated: {user_id}")
            return user
        except Exception as e:
            self.log_error(f"Error adding/updating user {user_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def update_user_activity(self, user_id: int):
        """Обновить время последней активности пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.last_activity = self.get_current_utc_time()
                session.commit()
                self.log_debug(f"User activity updated: {user_id}")
        except Exception as e:
            self.log_error(f"Error updating user activity {user_id}: {e}", exc_info=True)
            session.rollback()
        finally:
            session.close()

    def get_all_users(self, limit: int = None) -> List[User]:
        """Получить всех пользователей с поддержкой лимита"""
        session = self.get_session()
        try:
            query = session.query(User).filter_by(is_active=True)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            self.log_error(f"Error getting all users: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_all_users_generator(self, batch_size: int = 100):
        """Генератор для получения пользователей батчами (для больших объемов)"""
        session = self.get_session()
        try:
            offset = 0
            while True:
                users = session.query(User).filter_by(is_active=True)\
                    .offset(offset).limit(batch_size).all()
                if not users:
                    break
                for user in users:
                    yield user
                offset += batch_size
        except Exception as e:
            self.log_error(f"Error in users generator: {e}", exc_info=True)
        finally:
            session.close()

    def get_active_users_today(self) -> List[User]:
        """Получить пользователей, активных сегодня"""
        session = self.get_session()
        try:
            now = self.get_current_utc_time()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            
            users = session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start
            ).all()
            
            self.log_debug(f"Found {len(users)} active users today")
            return users
        except Exception as e:
            self.log_error(f"Error getting active users today: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_new_users(self, days: int = 7) -> List[User]:
        """Получить новых пользователей за указанное количество дней"""
        session = self.get_session()
        try:
            since_date = self.get_current_utc_time() - timedelta(days=days)
            
            users = session.query(User).filter(
                User.joined_at >= since_date
            ).all()
            
            self.log_debug(f"Found {len(users)} new users in last {days} days")
            return users
        except Exception as e:
            self.log_error(f"Error getting new users for {days} days: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_user_count(self) -> int:
        """Получить общее количество пользователей"""
        session = self.get_session()
        try:
            count = session.query(User).filter_by(is_active=True).count()
            return count
        except Exception as e:
            self.log_error(f"Error counting users: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def get_active_users_count_today(self) -> int:
        """Получить количество активных пользователей сегодня"""
        session = self.get_session()
        try:
            now = self.get_current_utc_time()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            
            count = session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting active users today: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def get_active_users_count_week(self) -> int:
        """Получить количество активных пользователей за неделю"""
        session = self.get_session()
        try:
            week_ago = self.get_current_utc_time() - timedelta(days=7)
            
            count = session.query(User).filter(
                User.is_active == True,
                User.last_activity >= week_ago
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting active users for week: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    def get_new_users_count(self, days: int = 1) -> int:
        """Получить количество новых пользователей за указанное количество дней"""
        session = self.get_session()
        try:
            since_date = self.get_current_utc_time() - timedelta(days=days)
            
            count = session.query(User).filter(
                User.joined_at >= since_date
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting new users for {days} days: {e}", exc_info=True)
            return 0
        finally:
            session.close()

    # Алиасы для удобства
    def get_new_users_count_week(self) -> int:
        """Количество новых пользователей за неделю"""
        return self.get_new_users_count(days=7)

    def get_new_users_count_month(self) -> int:
        """Количество новых пользователей за месяц"""
        return self.get_new_users_count(days=30)

    def get_new_users_week(self) -> List[User]:
        """Список новых пользователей за неделю"""
        return self.get_new_users(days=7)

    def get_new_users_month(self) -> List[User]:
        """Список новых пользователей за месяц"""
        return self.get_new_users(days=30)

    # МЕТОДЫ ДЛЯ РАССЫЛОК
    def create_mailing(self, title: str, message_text: str, message_type: str = "text", 
                      media_file_id: str = None, buttons: list = None, status: str = "draft",
                      trigger_word: str = None, is_trigger_mailing: bool = False,
                      document_original_name: str = None, document_mime_type: str = None,
                      document_file_size: int = None) -> Optional[Dict[str, Any]]:
        """Создать новую рассылку"""
        session = self.get_session()
        try:
            # Валидация кнопок
            buttons_json = None
            if buttons:
                try:
                    buttons_json = json.dumps(buttons)
                except (TypeError, ValueError, json.JSONDecodeError) as e:
                    self.log_error(f"Invalid buttons format: {e}")
                    buttons_json = "[]"
            else:
                buttons_json = "[]"
            
            mailing = Mailing(
                title=title,
                message_text=message_text,
                message_type=message_type,
                media_file_id=media_file_id,
                buttons=buttons_json,
                status=status,
                trigger_word=trigger_word,
                is_trigger_mailing=is_trigger_mailing,
                document_original_name=document_original_name,
                document_mime_type=document_mime_type,
                document_file_size=document_file_size
            )
            
            session.add(mailing)
            session.commit()
            
            self.log_info(f"New mailing created: '{title}' (ID: {mailing.id}, Type: {message_type})")
            return self._get_mailing_dict(mailing)
            
        except Exception as e:
            self.log_error(f"Error creating mailing '{title}': {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def update_mailing(self, mailing_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Обновить рассылку"""
        session = self.get_session()
        try:
            mailing = session.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                self.log_warning(f"Mailing {mailing_id} not found for update")
                return None
                
            for key, value in kwargs.items():
                if key == 'buttons' and isinstance(value, list):
                    try:
                        value = json.dumps(value)
                    except (TypeError, ValueError, json.JSONDecodeError) as e:
                        self.log_error(f"Invalid buttons format for mailing {mailing_id}: {e}")
                        continue
                setattr(mailing, key, value)
                
            mailing.updated_at = self.get_current_utc_time()
            session.commit()
            
            self.log_info(f"Mailing {mailing_id} updated: {list(kwargs.keys())}")
            return self._get_mailing_dict(mailing)
            
        except Exception as e:
            self.log_error(f"Error updating mailing {mailing_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def get_mailing(self, mailing_id: int) -> Optional[Dict[str, Any]]:
        """Получить рассылку по ID"""
        session = self.get_session()
        try:
            mailing = session.query(Mailing).filter_by(id=mailing_id).first()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            self.log_error(f"Error getting mailing {mailing_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_mailings_by_status(self, status: str, limit: int = None) -> List[Dict[str, Any]]:
        """Получить рассылки по статусу"""
        session = self.get_session()
        try:
            query = session.query(Mailing).filter_by(status=status)
            if limit:
                query = query.limit(limit)
                
            mailings = query.all()
            result = [self._get_mailing_dict(mailing) for mailing in mailings]
            
            self.log_debug(f"Found {len(result)} mailings with status '{status}'")
            return result
            
        except Exception as e:
            self.log_error(f"Error getting mailings by status '{status}': {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_all_mailings(self) -> List[Dict[str, Any]]:
        """Получить все рассылки (кроме удаленных)"""
        session = self.get_session()
        try:
            mailings = session.query(Mailing).filter(Mailing.status != 'deleted').all()
            result = [self._get_mailing_dict(mailing) for mailing in mailings]
            return result
        except Exception as e:
            self.log_error(f"Error getting all mailings: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def change_mailing_status(self, mailing_id: int, status: str) -> bool:
        """Изменить статус рассылки"""
        self.log_info(f"Changing mailing {mailing_id} status to '{status}'")
        return self.update_mailing(mailing_id, status=status) is not None

    def get_mailing_stats(self, mailing_id: int) -> Dict[str, Any]:
        """Получить статистику по рассылке"""
        session = self.get_session()
        try:
            stats = session.query(MailingStats).filter_by(mailing_id=mailing_id)
            total_sent = stats.count()
            delivered = stats.filter_by(delivered=True).count()
            read = stats.filter_by(read=True).count()
            
            success_rate = 0.0
            if total_sent > 0:
                success_rate = (delivered / total_sent) * 100
            
            return {
                'total_sent': total_sent,
                'delivered': delivered,
                'read': read,
                'success_rate': success_rate
            }
        except Exception as e:
            self.log_error(f"Error getting mailing stats for {mailing_id}: {e}", exc_info=True)
            return {'total_sent': 0, 'delivered': 0, 'read': 0, 'success_rate': 0.0}
        finally:
            session.close()

    def get_bulk_mailing_stats(self, mailing_ids: list) -> Dict[int, Dict[str, Any]]:
        """Получить статистику для нескольких рассылок за один запрос"""
        if not mailing_ids:
            return {}
            
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            result = session.query(
                MailingStats.mailing_id,
                func.count(MailingStats.id).label('total_sent'),
                func.sum(cast(MailingStats.delivered, Integer)).label('delivered'),
                func.sum(cast(MailingStats.read, Integer)).label('read')
            ).filter(
                MailingStats.mailing_id.in_(mailing_ids)
            ).group_by(
                MailingStats.mailing_id
            ).all()
            
            stats_dict = {}
            for row in result:
                total_sent = row.total_sent or 0
                delivered = row.delivered or 0
                read_count = row.read or 0
                
                success_rate = 0.0
                if total_sent > 0:
                    success_rate = (delivered / total_sent) * 100
                
                stats_dict[row.mailing_id] = {
                    'total_sent': total_sent,
                    'delivered': delivered,
                    'read': read_count,
                    'success_rate': success_rate
                }
            
            # Добавляем нулевые записи для рассылок без статистики
            for mailing_id in mailing_ids:
                if mailing_id not in stats_dict:
                    stats_dict[mailing_id] = {'total_sent': 0, 'delivered': 0, 'read': 0, 'success_rate': 0.0}
            
            return stats_dict
            
        except Exception as e:
            self.log_error(f"Error getting bulk mailing stats: {e}", exc_info=True)
            return {}
        finally:
            session.close()

    def add_mailing_stats(self, mailing_id: int, user_id: int, target_group: str) -> Optional[MailingStats]:
        """Добавить запись статистики для рассылки"""
        session = self.get_session()
        try:
            stats = MailingStats(
                mailing_id=mailing_id,
                user_id=user_id,
                target_group=target_group,
                sent_at=self.get_current_utc_time()
            )
            session.add(stats)
            session.commit()
            return stats
        except Exception as e:
            self.log_error(f"Error adding mailing stats for mailing {mailing_id}, user {user_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def update_mailing_stats(self, stats_id: int, **kwargs) -> Optional[MailingStats]:
        """Обновить статистику рассылки"""
        session = self.get_session()
        try:
            stats = session.query(MailingStats).filter_by(id=stats_id).first()
            if stats:
                for key, value in kwargs.items():
                    setattr(stats, key, value)
                    if key == 'delivered' and value:
                        stats.delivered_at = self.get_current_utc_time()
                    elif key == 'read' and value:
                        stats.read_at = self.get_current_utc_time()
                session.commit()
            return stats
        except Exception as e:
            self.log_error(f"Error updating mailing stats {stats_id}: {e}", exc_info=True)
            session.rollback()
            return None
        finally:
            session.close()

    def close(self):
        """Закрыть соединение с базой данных"""
        try:
            if hasattr(self, 'Session'):
                self.Session.close_all()
            if hasattr(self, 'engine'):
                self.engine.dispose()
            self.log_info("Database connection closed")
        except Exception as e:
            self.log_error(f"Error closing database: {e}", exc_info=True)

    def __del__(self):
        """Деструктор для автоматического закрытия соединения"""
        self.close()

# Создаем экземпляр базы данных
db = Database()