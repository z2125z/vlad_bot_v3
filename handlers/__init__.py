from .admin import router as admin_router
from .user import router as user_router
from .mailing_constructor import router as mailing_constructor_router

__all__ = ['admin_router', 'user_router', 'mailing_constructor_router']