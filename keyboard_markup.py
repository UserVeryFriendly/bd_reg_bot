from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_navigation_markup(items, callback_prefix, schema_name, page, page_size=10):
    """Создаёт разметку клавиатуры с кнопками для навигации"""
    markup = InlineKeyboardMarkup(row_width=2)
    start_idx = page * page_size
    end_idx = start_idx + page_size

    items_page = items[start_idx:end_idx]
    buttons = [
        InlineKeyboardButton(item, callback_data=f'{callback_prefix}|{schema_name}|{item}') for item in items_page
    ]

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("Предыдущая страница", callback_data=f'{callback_prefix}_prev|{schema_name}|{page - 1}'))
    if end_idx < len(items):
        nav_buttons.append(InlineKeyboardButton("Следующая страница", callback_data=f'{callback_prefix}_next|{schema_name}|{page + 1}'))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("Назад", callback_data=f'back|{schema_name}'))
    
    return markup