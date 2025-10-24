from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import config

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
    title = Column(String(200))
    message_text = Column(Text)
    message_type = Column(String(20))  # text, photo, video, document, voice, video_note
    media_file_id = Column(String(500))
    status = Column(String(20), default='draft')  # draft, active, archived, deleted
    buttons = Column(JSON)  # Список кнопок в формате [{"text": "Button", "url": "https://..."}]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MailingStats(Base):
    __tablename__ = 'mailing_stats'
    
    id = Column(Integer, primary_key=True)
    mailing_id = Column(Integer, ForeignKey('mailings.id'))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    target_group = Column(String(50))  # all, active_today, new
    sent = Column(Boolean, default=False)
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    
    mailing = relationship("Mailing", backref="stats")
    user = relationship("User")

class Database:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_user(self, user_id: int, username: str, full_name: str):
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id, username=username, full_name=full_name)
            self.session.add(user)
            self.session.commit()
        return user

    def update_user_activity(self, user_id: int):
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.last_activity = datetime.utcnow()
            self.session.commit()

    def get_all_users(self):
        return self.session.query(User).filter_by(is_active=True).all()

    def get_active_users_today(self):
        today = datetime.utcnow().date()
        return self.session.query(User).filter(
            User.is_active == True,
            User.last_activity >= today
        ).all()

    def get_new_users(self, days: int = 7):
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.session.query(User).filter(
            User.joined_at >= since_date
        ).all()

    def get_user_count(self):
        return self.session.query(User).filter_by(is_active=True).count()

    def get_active_users_count_today(self):
        today = datetime.utcnow().date()
        return self.session.query(User).filter(
            User.is_active == True,
            User.last_activity >= today
        ).count()

    def get_active_users_count_week(self):
        week_ago = datetime.utcnow() - timedelta(days=7)
        return self.session.query(User).filter(
            User.is_active == True,
            User.last_activity >= week_ago
        ).count()

    def get_new_users_count(self, days: int = 1):
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.session.query(User).filter(
            User.joined_at >= since_date
        ).count()

    def create_mailing(self, title: str, message_text: str, message_type: str = "text", 
                      media_file_id: str = None, buttons: list = None, status: str = "draft"):
        mailing = Mailing(
            title=title,
            message_text=message_text,
            message_type=message_type,
            media_file_id=media_file_id,
            buttons=buttons or [],
            status=status
        )
        self.session.add(mailing)
        self.session.commit()
        return mailing

    def update_mailing(self, mailing_id: int, **kwargs):
        mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
        if mailing:
            for key, value in kwargs.items():
                setattr(mailing, key, value)
            mailing.updated_at = datetime.utcnow()
            self.session.commit()
        return mailing

    def get_mailing(self, mailing_id: int):
        return self.session.query(Mailing).filter_by(id=mailing_id).first()

    def get_mailings_by_status(self, status: str):
        return self.session.query(Mailing).filter_by(status=status).all()

    def get_all_mailings(self):
        return self.session.query(Mailing).filter(Mailing.status != 'deleted').all()

    def change_mailing_status(self, mailing_id: int, status: str):
        return self.update_mailing(mailing_id, status=status)

    def get_mailing_stats(self, mailing_id: int):
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

    def get_mailing_detailed_stats(self, mailing_id: int):
        mailing = self.get_mailing(mailing_id)
        if not mailing:
            return None
            
        basic_stats = self.get_mailing_stats(mailing_id)
        
        # Группировка по целевым группам
        target_groups = self.session.query(
            MailingStats.target_group,
            func.count(MailingStats.id).label('count')
        ).filter_by(mailing_id=mailing_id).group_by(MailingStats.target_group).all()
        
        return {
            'mailing': mailing,
            **basic_stats,
            'target_groups': dict(target_groups)
        }

    def add_mailing_stats(self, mailing_id: int, user_id: int, target_group: str):
        stats = MailingStats(
            mailing_id=mailing_id,
            user_id=user_id,
            target_group=target_group,
            sent_at=datetime.utcnow()
        )
        self.session.add(stats)
        self.session.commit()
        return stats

    def update_mailing_stats(self, stats_id: int, **kwargs):
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

    def get_mailing_stats_by_user(self, mailing_id: int, user_id: int):
        return self.session.query(MailingStats).filter_by(
            mailing_id=mailing_id, 
            user_id=user_id
        ).first()

db = Database()