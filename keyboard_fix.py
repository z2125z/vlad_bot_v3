from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def combine_keyboards(main_keyboard: InlineKeyboardBuilder, pagination_keyboard: InlineKeyboardBuilder) -> InlineKeyboardBuilder:
    """Объединение двух клавиатур без ошибок"""
    result = InlineKeyboardBuilder()
    
    # Добавляем кнопки из основной клавиатуры
    if main_keyboard:
        # Получаем все кнопки из main_keyboard
        for row in main_keyboard.export():
            for button in row:
                if isinstance(button, InlineKeyboardButton):
                    result.add(button)
    
    # Добавляем кнопки из клавиатуры пагинации
    if pagination_keyboard:
        # Получаем все кнопки из pagination_keyboard
        for row in pagination_keyboard.export():
            for button in row:
                if isinstance(button, InlineKeyboardButton):
                    result.add(button)
    
    # Настраиваем расположение (1 кнопка в ряд для рассылок, 3 для пагинации)
    result.adjust(1, 3)
    return result

def create_simple_pagination(current_page: int, total_pages: int, callback_prefix: str):
    """Создание простой клавиатуры пагинации"""
    keyboard = InlineKeyboardBuilder()
    
    # Кнопки перехода
    if current_page > 1:
        keyboard.add(InlineKeyboardButton(
            text="◀️ Назад", 
            callback_data=f"{callback_prefix}_{current_page - 1}"
        ))
    
    # Номер страницы
    keyboard.add(InlineKeyboardButton(
        text=f"📄 {current_page}/{total_pages}", 
        callback_data="noop"
    ))
    
    if current_page < total_pages:
        keyboard.add(InlineKeyboardButton(
            text="Вперед ▶️", 
            callback_data=f"{callback_prefix}_{current_page + 1}"
        ))
    
    # Кнопка назад в главное меню рассылок
    keyboard.add(InlineKeyboardButton(
        text="🔙 К меню рассылок", 
        callback_data="admin_mailings"
    ))
    
    keyboard.adjust(3)
    return keyboard