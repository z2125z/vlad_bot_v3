from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
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
    message_type = Column(String(20))  # text, photo, document
    file_id = Column(String(300))
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)

class MailingStats(Base):
    __tablename__ = 'mailing_stats'
    
    id = Column(Integer, primary_key=True)
    mailing_id = Column(Integer)
    user_id = Column(Integer)
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)

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

    def get_all_users(self):
        return self.session.query(User).filter_by(is_active=True).all()

    def get_user_count(self):
        return self.session.query(User).filter_by(is_active=True).count()

    def create_mailing(self, title: str, message_text: str, message_type: str = "text", file_id: str = None):
        mailing = Mailing(
            title=title,
            message_text=message_text,
            message_type=message_type,
            file_id=file_id
        )
        self.session.add(mailing)
        self.session.commit()
        return mailing

    def get_mailing_stats(self, mailing_id: int):
        mailing = self.session.query(Mailing).filter_by(id=mailing_id).first()
        stats = self.session.query(MailingStats).filter_by(mailing_id=mailing_id)
        return {
            'mailing': mailing,
            'total_sent': stats.count(),
            'delivered': stats.filter_by(delivered=True).count(),
            'read': stats.filter_by(read=True).count()
        }

    def update_user_activity(self, user_id: int):
        user = self.session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.last_activity = datetime.utcnow()
            self.session.commit()

db = Database()