from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

page_size=10

def create_navigation_markup(object_ids, callback_prefix, schema_id, page, ad_pref=''):
    """Создаёт разметку клавиатуры с кнопками для навигации"""
    logging.info(f"Создание навигационной разметки с schema_id: {schema_id}, page: {page}, page_size: {page_size}")
    markup = InlineKeyboardMarkup(row_width=2)
    start_idx = page * page_size
    end_idx = start_idx + page_size

    items_page = list(object_ids.items())[start_idx:end_idx]

    buttons = [
        InlineKeyboardButton(name, callback_data=f'{callback_prefix}{ad_pref}|{schema_id}|{object_id}') 
        for name, object_id in items_page
    ]

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая страница", callback_data=f'{callback_prefix}{ad_pref}_prev|{schema_id}|{page - 1}'))
    if end_idx < len(object_ids):
        nav_buttons.append(InlineKeyboardButton("Следующая страница ➡️", callback_data=f'{callback_prefix}{ad_pref}_next|{schema_id}|{page + 1}'))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("Назад", callback_data=f'back{ad_pref}|{schema_id}'))
    
    return markup, ad_pref

def create_user_navigation_markup(users, callback_prefix, schema_id, object_id, object_type, page, ad_pref=''):
    """Создаёт разметку клавиатуры с кнопками для навигации для выбора пользователей"""
    logging.info(f"Создание навигационной разметки для выбора пользователей с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}, page: {page}, page_size: {page_size}")
    markup = InlineKeyboardMarkup(row_width=2)
    start_idx = page * page_size
    end_idx = start_idx + page_size

    users_page = list(users.items())[start_idx:end_idx]
    buttons = [
        InlineKeyboardButton(user_name, callback_data=f'{callback_prefix}{ad_pref}|{schema_id}|{object_id}|{user_id}|{object_type}') 
        for user_name, user_id in users_page
    ]

    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая страница", callback_data=f'{callback_prefix}{ad_pref}_prev|{schema_id}|{object_id}|{page - 1}|{object_type}'))
    if end_idx < len(users):
        nav_buttons.append(InlineKeyboardButton("Следующая страница ➡️", callback_data=f'{callback_prefix}{ad_pref}_next|{schema_id}|{object_id}|{page + 1}|{object_type}'))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(InlineKeyboardButton("Назад", callback_data=f'choose_{object_type}{ad_pref}|{schema_id}|{object_id}'))

    return markup