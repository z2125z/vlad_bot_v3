from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime, timedelta
import config
import json
import pytz
import logging

# Создаем локальный логгер для этого модуля
logger = logging.getLogger('database')

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Индексы для производительности
    __table_args__ = (
        Index('ix_users_user_id', 'user_id'),
        Index('ix_users_last_activity', 'last_activity'),
        Index('ix_users_joined_at', 'joined_at'),
        Index('ix_users_is_active', 'is_active'),
    )

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
    status = Column(String(50), default='draft')
    buttons = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    trigger_word = Column(String(100), nullable=True)
    is_trigger_mailing = Column(Boolean, default=False)

    # Индексы для производительности
    __table_args__ = (
        Index('ix_mailings_status', 'status'),
        Index('ix_mailings_created_at', 'created_at'),
        Index('ix_mailings_trigger_word', 'trigger_word'),
        Index('ix_mailings_is_trigger_mailing', 'is_trigger_mailing'),
    )

class MailingStats(Base):
    __tablename__ = 'mailing_stats'
    
    id = Column(Integer, primary_key=True)
    mailing_id = Column(Integer, ForeignKey('mailings.id'))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    target_group = Column(String(50))
    sent = Column(Boolean, default=False)
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    mailing = relationship("Mailing", backref="stats")
    user = relationship("User")

    # Индексы для производительности
    __table_args__ = (
        Index('ix_mailing_stats_mailing_id', 'mailing_id'),
        Index('ix_mailing_stats_user_id', 'user_id'),
        Index('ix_mailing_stats_sent_at', 'sent_at'),
        Index('ix_mailing_stats_delivered', 'delivered'),
    )


class Database:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
        self._setup_logger()
        self._create_tables()
        Session = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False))
        self.session = Session()
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
            raise

    def get_current_utc_time(self):
        """Получить текущее время в UTC"""
        return datetime.utcnow()

    def _get_mailing_dict(self, mailing):
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
            'created_at': mailing.created_at,
            'updated_at': mailing.updated_at
        }
        
        # Безопасная обработка кнопок
        if mailing.buttons:
            try:
                mailing_dict['buttons'] = json.loads(mailing.buttons)
            except (json.JSONDecodeError, TypeError) as e:
                self.log_warning(f"Error parsing buttons for mailing {mailing.id}: {e}")
                mailing_dict['buttons'] = []
        else:
            mailing_dict['buttons'] = []
            
        return mailing_dict

    # МЕТОДЫ ДЛЯ ПРИВЕТСТВЕННЫХ СООБЩЕНИЙ
    def get_welcome_message(self):
        """Получить активное приветственное сообщение"""
        try:
            welcome = self.session.query(WelcomeMessage).filter_by(is_active=True).first()
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

    def update_welcome_message(self, message_text: str, message_type: str = "text", media_file_id: str = None):
        """Обновить приветственное сообщение"""
        try:
            # Деактивируем все существующие
            self.session.query(WelcomeMessage).update({'is_active': False})
            
            # Создаем новое
            welcome = WelcomeMessage(
                message_text=message_text,
                message_type=message_type,
                media_file_id=media_file_id,
                is_active=True
            )
            self.session.add(welcome)
            self.session.commit()
            self.log_info("Welcome message updated")
            return True
        except Exception as e:
            self.log_error(f"Error updating welcome message: {e}", exc_info=True)
            self.session.rollback()
            return False

    # МЕТОДЫ ДЛЯ РАССЫЛОК ПО ЗАПРОСУ
    def get_active_trigger_mailings(self):
        """Получить все активные рассылки по запросу"""
        try:
            mailings = self.session.query(Mailing).filter(
                Mailing.is_trigger_mailing == True,
                Mailing.status == 'active'
            ).all()
            return [self._get_mailing_dict(mailing) for mailing in mailings]
        except Exception as e:
            self.log_error(f"Error getting active trigger mailings: {e}", exc_info=True)
            return []

    def get_mailing_by_trigger_word(self, trigger_word: str):
        """Найти рассылку по кодовому слову"""
        try:
            mailing = self.session.query(Mailing).filter(
                Mailing.trigger_word == trigger_word,
                Mailing.is_trigger_mailing == True,
                Mailing.status == 'active'
            ).first()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            self.log_error(f"Error getting mailing by trigger word '{trigger_word}': {e}", exc_info=True)
            return None

    # ОПТИМИЗИРОВАННЫЕ МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
    def get_user(self, user_id: int):
        """Получить пользователя по ID"""
        try:
            return self.session.query(User).filter_by(user_id=user_id).first()
        except Exception as e:
            self.log_error(f"Error getting user {user_id}: {e}", exc_info=True)
            return None

    def add_user(self, user_id: int, username: str, full_name: str):
        """Добавить нового пользователя или обновить существующего"""
        try:
            user = self.session.query(User).filter_by(user_id=user_id).first()
            if not user:
                user = User(user_id=user_id, username=username, full_name=full_name)
                self.session.add(user)
                self.session.commit()
                self.log_info(f"New user added: {user_id} (@{username})")
            elif user.username != username or user.full_name != full_name:
                # Обновляем информацию если изменилась
                user.username = username
                user.full_name = full_name
                self.session.commit()
                self.log_info(f"User info updated: {user_id}")
            return user
        except Exception as e:
            self.log_error(f"Error adding/updating user {user_id}: {e}", exc_info=True)
            self.session.rollback()
            return None

    def update_user_activity(self, user_id: int):
        """Обновить время последней активности пользователя"""
        try:
            user = self.session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.last_activity = datetime.utcnow()
                self.session.commit()
                self.log_debug(f"User activity updated: {user_id}")
        except Exception as e:
            self.log_error(f"Error updating user activity {user_id}: {e}", exc_info=True)
            self.session.rollback()

    def get_all_users(self, limit: int = None):
        """Получить всех пользователей с поддержкой лимита"""
        try:
            query = self.session.query(User).filter_by(is_active=True)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            self.log_error(f"Error getting all users: {e}", exc_info=True)
            return []

    def get_all_users_generator(self, batch_size: int = 100):
        """Генератор для получения пользователей батчами (для больших объемов)"""
        try:
            offset = 0
            while True:
                users = self.session.query(User).filter_by(is_active=True)\
                    .offset(offset).limit(batch_size).all()
                if not users:
                    break
                for user in users:
                    yield user
                offset += batch_size
        except Exception as e:
            self.log_error(f"Error in users generator: {e}", exc_info=True)

    def get_active_users_today(self):
        """Получить пользователей, активных сегодня"""
        try:
            now = datetime.utcnow()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
            
            users = self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start,
                User.last_activity <= today_end
            ).all()
            
            self.log_debug(f"Found {len(users)} active users today")
            return users
        except Exception as e:
            self.log_error(f"Error getting active users today: {e}", exc_info=True)
            return []

    def get_new_users(self, days: int = 7):
        """Получить новых пользователей за указанное количество дней"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            users = self.session.query(User).filter(
                User.joined_at >= since_date
            ).all()
            
            self.log_debug(f"Found {len(users)} new users in last {days} days")
            return users
        except Exception as e:
            self.log_error(f"Error getting new users for {days} days: {e}", exc_info=True)
            return []

    def get_user_count(self):
        """Получить общее количество пользователей"""
        try:
            count = self.session.query(User).filter_by(is_active=True).count()
            return count
        except Exception as e:
            self.log_error(f"Error counting users: {e}", exc_info=True)
            return 0

    def get_active_users_count_today(self):
        """Получить количество активных пользователей сегодня"""
        try:
            now = datetime.utcnow()
            today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
            today_end = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
            
            count = self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start,
                User.last_activity <= today_end
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting active users today: {e}", exc_info=True)
            return 0

    def get_active_users_count_week(self):
        """Получить количество активных пользователей за неделю"""
        try:
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            count = self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= week_ago
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting active users for week: {e}", exc_info=True)
            return 0

    def get_new_users_count(self, days: int = 1):
        """Получить количество новых пользователей за указанное количество дней"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            count = self.session.query(User).filter(
                User.joined_at >= since_date
            ).count()
            
            return count
        except Exception as e:
            self.log_error(f"Error counting new users for {days} days: {e}", exc_info=True)
            return 0

    # Алиасы для удобства
    def get_new_users_count_week(self):
        """Количество новых пользователей за неделю"""
        return self.get_new_users_count(days=7)

    def get_new_users_count_month(self):
        """Количество новых пользователей за месяц"""
        return self.get_new_users_count(days=30)

    def get_new_users_week(self):
        """Список новых пользователей за неделю"""
        return self.get_new_users(days=7)

    def get_new_users_month(self):
        """Список новых пользователей за месяц"""
        return self.get_new_users(days=30)

    # МЕТОДЫ ДЛЯ РАССЫЛОК
    def create_mailing(self, title: str, message_text: str, message_type: str = "text", 
                      media_file_id: str = None, buttons: list = None, status: str = "draft",
                      trigger_word: str = None, is_trigger_mailing: bool = False):
        """Создать новую рассылку"""
        try:
            # Валидация кнопок
            if buttons:
                try:
                    buttons_json = json.dumps(buttons)
                except (TypeError, ValueError) as e:
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
                is_trigger_mailing=is_trigger_mailing
            )
            
            self.session.add(mailing)
            self.session.commit()
            
            self.log_info(f"New mailing created: '{title}' (ID: {mailing.id}, Type: {message_type})")
            return self._get_mailing_dict(mailing)
            
        except Exception as e:
            self.log_error(f"Error creating mailing '{title}': {e}", exc_info=True)
            self.session.rollback()
            return None

    def update_mailing(self, mailing_id: int, **kwargs):
        """Обновить рассылку"""
        try:
            mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
            if not mailing:
                self.log_warning(f"Mailing {mailing_id} not found for update")
                return None
                
            for key, value in kwargs.items():
                if key == 'buttons' and isinstance(value, list):
                    try:
                        value = json.dumps(value)
                    except (TypeError, ValueError) as e:
                        self.log_error(f"Invalid buttons format for mailing {mailing_id}: {e}")
                        continue
                setattr(mailing, key, value)
                
            mailing.updated_at = datetime.utcnow()
            self.session.commit()
            
            self.log_info(f"Mailing {mailing_id} updated: {list(kwargs.keys())}")
            return self._get_mailing_dict(mailing)
            
        except Exception as e:
            self.log_error(f"Error updating mailing {mailing_id}: {e}", exc_info=True)
            self.session.rollback()
            return None

    def get_mailing(self, mailing_id: int):
        """Получить рассылку по ID"""
        try:
            mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            self.log_error(f"Error getting mailing {mailing_id}: {e}", exc_info=True)
            return None

    def get_mailings_by_status(self, status: str, limit: int = None):
        """Получить рассылки по статусу"""
        try:
            query = self.session.query(Mailing).filter_by(status=status)
            if limit:
                query = query.limit(limit)
                
            mailings = query.all()
            result = [self._get_mailing_dict(mailing) for mailing in mailings]
            
            self.log_debug(f"Found {len(result)} mailings with status '{status}'")
            return result
            
        except Exception as e:
            self.log_error(f"Error getting mailings by status '{status}': {e}", exc_info=True)
            return []

    def get_all_mailings(self):
        """Получить все рассылки (кроме удаленных)"""
        try:
            mailings = self.session.query(Mailing).filter(Mailing.status != 'deleted').all()
            result = [self._get_mailing_dict(mailing) for mailing in mailings]
            return result
        except Exception as e:
            self.log_error(f"Error getting all mailings: {e}", exc_info=True)
            return []

    def change_mailing_status(self, mailing_id: int, status: str):
        """Изменить статус рассылки"""
        self.log_info(f"Changing mailing {mailing_id} status to '{status}'")
        return self.update_mailing(mailing_id, status=status)

    def get_mailing_stats(self, mailing_id: int):
        """Получить статистику по рассылке"""
        try:
            stats = self.session.query(MailingStats).filter_by(mailing_id=mailing_id)
            total_sent = stats.count()
            delivered = stats.filter_by(delivered=True).count()
            read = stats.filter_by(read=True).count()
            
            return {
                'total_sent': total_sent,
                'delivered': delivered,
                'read': read,
                'success_rate': (delivered / total_sent * 100) if total_sent > 0 else 0
            }
        except Exception as e:
            self.log_error(f"Error getting mailing stats for {mailing_id}: {e}", exc_info=True)
            return {'total_sent': 0, 'delivered': 0, 'read': 0, 'success_rate': 0}

    def get_bulk_mailing_stats(self, mailing_ids: list):
        """Получить статистику для нескольких рассылок за один запрос"""
        try:
            from sqlalchemy import func
            
            result = self.session.query(
                MailingStats.mailing_id,
                func.count(MailingStats.id).label('total_sent'),
                func.sum(func.cast(MailingStats.delivered, Integer)).label('delivered'),
                func.sum(func.cast(MailingStats.read, Integer)).label('read')
            ).filter(
                MailingStats.mailing_id.in_(mailing_ids)
            ).group_by(
                MailingStats.mailing_id
            ).all()
            
            stats_dict = {}
            for row in result:
                stats_dict[row.mailing_id] = {
                    'total_sent': row.total_sent,
                    'delivered': row.delivered or 0,
                    'read': row.read or 0,
                    'success_rate': (row.delivered / row.total_sent * 100) if row.total_sent > 0 else 0
                }
            
            # Добавляем нулевые записи для рассылок без статистики
            for mailing_id in mailing_ids:
                if mailing_id not in stats_dict:
                    stats_dict[mailing_id] = {'total_sent': 0, 'delivered': 0, 'read': 0, 'success_rate': 0}
            
            return stats_dict
            
        except Exception as e:
            self.log_error(f"Error getting bulk mailing stats: {e}", exc_info=True)
            return {}

    def add_mailing_stats(self, mailing_id: int, user_id: int, target_group: str):
        """Добавить запись статистики для рассылки"""
        try:
            stats = MailingStats(
                mailing_id=mailing_id,
                user_id=user_id,
                target_group=target_group,
                sent_at=datetime.utcnow()
            )
            self.session.add(stats)
            self.session.commit()
            return stats
        except Exception as e:
            self.log_error(f"Error adding mailing stats for mailing {mailing_id}, user {user_id}: {e}", exc_info=True)
            self.session.rollback()
            return None

    def update_mailing_stats(self, stats_id: int, **kwargs):
        """Обновить статистику рассылки"""
        try:
            stats = self.session.query(MailingStats).filter_by(id=stats_id).first()
            if stats:
                for key, value in kwargs.items():
                    setattr(stats, key, value)
                    if key == 'delivered' and value:
                        stats.delivered_at = datetime.utcnow()
                    elif key == 'read' and value:
                        stats.read_at = datetime.utcnow()
                self.session.commit()
            return stats
        except Exception as e:
            self.log_error(f"Error updating mailing stats {stats_id}: {e}", exc_info=True)
            self.session.rollback()
            return None

    def close(self):
        """Закрыть соединение с базой данных"""
        try:
            self.session.remove()
            self.engine.dispose()
            self.log_info("Database connection closed")
        except Exception as e:
            self.log_error(f"Error closing database: {e}", exc_info=True)

    def __del__(self):
        """Деструктор для автоматического закрытия соединения"""
        self.close()


# Создаем экземпляр базы данных
db = Database()