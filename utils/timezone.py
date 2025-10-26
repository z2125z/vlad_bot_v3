from datetime import datetime
import pytz

# Московская временная зона
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def get_moscow_time():
    """Получить текущее время в Москве"""
    return datetime.now(MOSCOW_TZ)

def utc_to_moscow(utc_dt):
    """Конвертировать UTC время в московское"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(MOSCOW_TZ)

def moscow_to_utc(moscow_dt):
    """Конвертировать московское время в UTC"""
    if moscow_dt is None:
        return None
    if moscow_dt.tzinfo is None:
        moscow_dt = MOSCOW_TZ.localize(moscow_dt)
    return moscow_dt.astimezone(pytz.utc)

def format_moscow_time(dt=None, format_str='%d.%m.%Y %H:%M'):
    """Форматировать время в московском формате"""
    if dt is None:
        dt = get_moscow_time()
    elif dt.tzinfo is None:
        dt = utc_to_moscow(dt)
    else:
        dt = dt.astimezone(MOSCOW_TZ)
    
    return dt.strftime(format_str)

def get_moscow_date():
    """Получить текущую дату в Москве"""
    return get_moscow_time().date()

def get_moscow_datetime():
    """Получить текущую дату и время в Москве"""
    return get_moscow_time()