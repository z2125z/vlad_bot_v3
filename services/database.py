from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime, timedelta
import config
import json
import pytz

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

class Database:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        self._create_tables()
        Session = scoped_session(sessionmaker(bind=self.engine))
        self.session = Session()

    def _create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            Base.metadata.create_all(self.engine)
            print("Таблицы созданы/проверены")
        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")

    def _get_moscow_time(self):
        """Локальный импорт для избежания циклических импортов"""
        from utils.timezone import get_moscow_time, utc_to_moscow, moscow_to_utc
        return get_moscow_time(), utc_to_moscow, moscow_to_utc

    def _get_mailing_dict(self, mailing):
        """Преобразует объект Mailing в словарь с московским временем"""
        if not mailing:
            return None
            
        _, utc_to_moscow, _ = self._get_moscow_time()
            
        mailing_dict = {
            'id': mailing.id,
            'title': mailing.title,
            'message_text': mailing.message_text,
            'message_type': mailing.message_type,
            'media_file_id': mailing.media_file_id,
            'status': mailing.status,
            'created_at': utc_to_moscow(mailing.created_at) if mailing.created_at else None,
            'updated_at': utc_to_moscow(mailing.updated_at) if mailing.updated_at else None
        }
        
        if mailing.buttons:
            try:
                mailing_dict['buttons'] = json.loads(mailing.buttons)
            except:
                mailing_dict['buttons'] = []
        else:
            mailing_dict['buttons'] = []
            
        return mailing_dict

    def add_user(self, user_id: int, username: str, full_name: str):
        try:
            user = self.session.query(User).filter_by(user_id=user_id).first()
            if not user:
                user = User(user_id=user_id, username=username, full_name=full_name)
                self.session.add(user)
                self.session.commit()
            return user
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            self.session.rollback()
            return None

    def update_user_activity(self, user_id: int):
        try:
            user = self.session.query(User).filter_by(user_id=user_id).first()
            if user:
                user.last_activity = datetime.utcnow()
                self.session.commit()
        except Exception as e:
            print(f"Ошибка при обновлении активности: {e}")
            self.session.rollback()

    def get_all_users(self):
        try:
            return self.session.query(User).filter_by(is_active=True).all()
        except Exception as e:
            print(f"Ошибка при получении пользователей: {e}")
            return []

    def get_active_users_today(self):
        try:
            # Используем локальный импорт
            get_moscow_time, _, moscow_to_utc = self._get_moscow_time()
            today_moscow = get_moscow_time().date()
            today_start = moscow_to_utc(datetime.combine(today_moscow, datetime.min.time()))
            today_end = moscow_to_utc(datetime.combine(today_moscow, datetime.max.time()))
            
            return self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start,
                User.last_activity <= today_end
            ).all()
        except Exception as e:
            print(f"Ошибка при получении активных пользователей: {e}")
            return []

    def get_new_users(self, days: int = 7):
        try:
            get_moscow_time, _, moscow_to_utc = self._get_moscow_time()
            since_date = moscow_to_utc(get_moscow_time() - timedelta(days=days))
            return self.session.query(User).filter(
                User.joined_at >= since_date
            ).all()
        except Exception as e:
            print(f"Ошибка при получении новых пользователей: {e}")
            return []

    def get_user_count(self):
        try:
            return self.session.query(User).filter_by(is_active=True).count()
        except Exception as e:
            print(f"Ошибка при подсчете пользователей: {e}")
            return 0

    def get_active_users_count_today(self):
        try:
            get_moscow_time, _, moscow_to_utc = self._get_moscow_time()
            today_moscow = get_moscow_time().date()
            today_start = moscow_to_utc(datetime.combine(today_moscow, datetime.min.time()))
            today_end = moscow_to_utc(datetime.combine(today_moscow, datetime.max.time()))
            
            return self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= today_start,
                User.last_activity <= today_end
            ).count()
        except Exception as e:
            print(f"Ошибка при подсчете активных пользователей: {e}")
            return 0

    def get_active_users_count_week(self):
        try:
            get_moscow_time, _, moscow_to_utc = self._get_moscow_time()
            week_ago = moscow_to_utc(get_moscow_time() - timedelta(days=7))
            return self.session.query(User).filter(
                User.is_active == True,
                User.last_activity >= week_ago
            ).count()
        except Exception as e:
            print(f"Ошибка при подсчете активных за неделю: {e}")
            return 0

    def get_new_users_count(self, days: int = 1):
        try:
            get_moscow_time, _, moscow_to_utc = self._get_moscow_time()
            since_date = moscow_to_utc(get_moscow_time() - timedelta(days=days))
            return self.session.query(User).filter(
                User.joined_at >= since_date
            ).count()
        except Exception as e:
            print(f"Ошибка при подсчете новых пользователей: {e}")
            return 0

    def create_mailing(self, title: str, message_text: str, message_type: str = "text", 
                      media_file_id: str = None, buttons: list = None, status: str = "draft"):
        try:
            buttons_json = json.dumps(buttons or [])
            
            mailing = Mailing(
                title=title,
                message_text=message_text,
                message_type=message_type,
                media_file_id=media_file_id,
                buttons=buttons_json,
                status=status
            )
            self.session.add(mailing)
            self.session.commit()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            print(f"Ошибка при создании рассылки: {e}")
            self.session.rollback()
            return None

    def update_mailing(self, mailing_id: int, **kwargs):
        try:
            mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
            if mailing:
                for key, value in kwargs.items():
                    if key == 'buttons' and isinstance(value, list):
                        value = json.dumps(value)
                    setattr(mailing, key, value)
                mailing.updated_at = datetime.utcnow()
                self.session.commit()
                return self._get_mailing_dict(mailing)
            return None
        except Exception as e:
            print(f"Ошибка при обновлении рассылки: {e}")
            self.session.rollback()
            return None

    def get_mailing(self, mailing_id: int):
        try:
            mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
            return self._get_mailing_dict(mailing)
        except Exception as e:
            print(f"Ошибка при получении рассылки: {e}")
            return None

    def get_mailings_by_status(self, status: str):
        try:
            mailings = self.session.query(Mailing).filter_by(status=status).all()
            return [self._get_mailing_dict(mailing) for mailing in mailings]
        except Exception as e:
            print(f"Ошибка при получении рассылок по статусу: {e}")
            return []

    def get_all_mailings(self):
        try:
            mailings = self.session.query(Mailing).filter(Mailing.status != 'deleted').all()
            return [self._get_mailing_dict(mailing) for mailing in mailings]
        except Exception as e:
            print(f"Ошибка при получении всех рассылок: {e}")
            return []

    def change_mailing_status(self, mailing_id: int, status: str):
        return self.update_mailing(mailing_id, status=status)

    def get_mailing_stats(self, mailing_id: int):
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
            print(f"Ошибка при получении статистики рассылки: {e}")
            return {'total_sent': 0, 'delivered': 0, 'read': 0, 'success_rate': 0}

    def add_mailing_stats(self, mailing_id: int, user_id: int, target_group: str):
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
            print(f"Ошибка при добавлении статистики: {e}")
            self.session.rollback()
            return None

    def update_mailing_stats(self, stats_id: int, **kwargs):
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
            print(f"Ошибка при обновлении статистики: {e}")
            self.session.rollback()
            return None

# Создаем экземпляр базы данных
db = Database()