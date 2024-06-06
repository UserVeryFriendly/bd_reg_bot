from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import logging
from db_connection import connect_to_db
from db_gets import list_objects, get_schemas, get_users
from keyboard_markup import create_navigation_markup

connection, cursor = connect_to_db()

logging.basicConfig(level=logging.INFO)

# ===================== Функции взаимодействия с пользователем =====================

def send_welcome(bot, message: Message):
    '''Отправляет приветственное сообщение'''
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("Администратор", callback_data='admin_menu'),
        InlineKeyboardButton("Запрос доступа", callback_data='request_access')
    ]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите нужный раздел:", reply_markup=markup)
    logging.info("Отправлено начальное сообщение с выбором функций")

def request_access(bot, message: Message):
    '''Отправляет сообщение о недоступности функционала запроса доступа с кнопкой назад'''
    markup = InlineKeyboardMarkup(row_width=1)
    button_back = InlineKeyboardButton("Назад", callback_data='back_main')
    markup.add(button_back)
    bot.edit_message_text("Функционал запроса доступа пока не реализован.", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Обработан запрос доступа")

def show_admin_menu(bot, message: Message):
    '''Отображает меню администратора с выбором схем'''
    schemas = get_schemas()
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema}') for schema in schemas]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))
    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Показано административное меню с выбором схем")

def show_schema_options(bot, message: Message, schema_name: str, call: CallbackQuery):
    '''Отображает опции для выбранной схемы'''
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Выдать права", callback_data=f'grant|{schema_name}'))
    markup.add(InlineKeyboardButton("Посмотреть таблицы", callback_data=f'tables|{schema_name}|0'))
    markup.add(InlineKeyboardButton("Посмотреть вью", callback_data=f'views|{schema_name}|0'))
    markup.add(InlineKeyboardButton("Назад", callback_data='admin_menu'))

    bot.edit_message_text(f"Опции для схемы {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показаны опции для схемы {schema_name}")


# ===================== Функции работы с пользовательскими правами =====================

def request_user_for_permissions(bot, call: CallbackQuery, schema_name: str, object_name: str, object_type: str, page: int = 0):
    '''Запрашивает пользователя для выдачи прав на указанный объект'''
    users = get_users()
    if not users:
        bot.send_message(call.message.chat.id, "Нет доступных пользователей для выдачи прав.")
        logging.info("Нет доступных пользователей для выдачи прав.")
        return

    callback_prefix = f'grant_{object_type}_perm'
    markup = create_navigation_markup(users, callback_prefix, schema_name, page)

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на {object_type} {object_name} в схеме {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Выбор пользователя для выдачи прав на {object_type} {object_name} в схеме {schema_name}, страница {page}")

def grant_permissions(bot, call: CallbackQuery, schema_name: str, object_name: str, user_to_grant: str, object_type: str):
    '''Выдаёт права на указанный объект пользователю'''
    try:
        key = f"{schema_name}|{object_name}"
        permissions = selected_permissions.get(key, set())
        if not permissions:
            bot.answer_callback_query(call.id, text=f"Не выбрано ни одного права для {object_type} {object_name}.")
            return

        permissions_str = ', '.join(permissions)
        cursor.execute(f"GRANT {permissions_str} ON TABLE {schema_name}.{object_name} TO {user_to_grant}")

        connection.commit()

        bot.answer_callback_query(call.id, text=f"Выданы права ({permissions_str}) на {object_type} {object_name} пользователю {user_to_grant}.")
        logging.info(f"Права ({permissions_str}) на {object_type} {object_name} выданы для пользователя {user_to_grant}")

        selected_permissions.pop(key, None)

    except Exception as e:
        bot.answer_callback_query(call.id, text=f"Ошибка при выдаче прав: {e}")
        logging.error(f"Ошибка при выдаче прав: {e}")

    edit_to_welcome(bot, call.message)

def request_user_for_grant(bot, call: CallbackQuery, schema_name: str, page: int = 0):
    '''Запрашивает пользователя для выдачи прав на схему'''
    users = get_users()
    if not users:
        bot.send_message(call.message.chat.id, "Нет доступных пользователей для выдачи прав.")
        logging.info("Нет доступных пользователей для выдачи прав.")
        return

    callback_prefix = 'choose_perm'
    markup = create_navigation_markup(users, callback_prefix, schema_name, page)

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показан список пользователей для схемы {schema_name}, страница {page}")

def grant_usage_to_schema(bot, call: CallbackQuery, schema_name: str, user_to_grant: str, permission_type: str):
    '''Выдаёт права на использование или создание объектов в схеме'''
    try:
        if permission_type == 'usage':
            cursor.execute(f"GRANT USAGE ON SCHEMA {schema_name} TO {user_to_grant}")
        elif permission_type == 'create_usage':
            cursor.execute(f"GRANT USAGE, CREATE ON SCHEMA {schema_name} TO {user_to_grant}")
        connection.commit()
        bot.answer_callback_query(call.id, text=f"Выдано право на {permission_type} схемы {schema_name} пользователю {user_to_grant}")
        logging.info(f"Права на {permission_type} схемы {schema_name} выданы для пользователя {user_to_grant}")
    except Exception as e:
        bot.answer_callback_query(call.id, text=f"Ошибка при выдаче прав: {e}")
        logging.error(f"Ошибка при выдаче прав: {e}")

    edit_to_welcome(bot, call.message)

def choose_permission(bot, call: CallbackQuery, schema_name: str, user_to_grant: str):
    '''Запрашивает тип прав для пользователя на схему'''
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Usage", callback_data=f'grant_permission|usage|{schema_name}|{user_to_grant}'))
    markup.add(InlineKeyboardButton("Create + Usage", callback_data=f'grant_permission|create_usage|{schema_name}|{user_to_grant}'))
    markup.add(InlineKeyboardButton("Назад", callback_data=f'grant|{schema_name}'))  

    bot.edit_message_text(f"Выберите тип прав для пользователя {user_to_grant} на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Нужен выбор типа прав для пользователя {user_to_grant} на схему {schema_name}")

selected_permissions = {}

def choose_permissions(bot, call: CallbackQuery, schema_name: str, object_name: str, object_type: str):
    '''Выбор и отображение прав для указанного объекта'''
    permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER']
    key = f"{schema_name}|{object_name}"
    selected = selected_permissions.get(key, set())

    markup = InlineKeyboardMarkup()
    for perm in permissions:
        if perm in selected:
            markup.add(InlineKeyboardButton(f"{perm} ✅", callback_data=f'toggle_perm|{schema_name}|{object_name}|{object_type}|{perm}'))
        else:
            markup.add(InlineKeyboardButton(perm, callback_data=f'toggle_perm|{schema_name}|{object_name}|{object_type}|{perm}'))

    markup.add(InlineKeyboardButton("Выберите пользователя", callback_data=f'choose_user|{schema_name}|{object_name}|{object_type}'))
    markup.add(InlineKeyboardButton("Назад", callback_data=f'grant|{schema_name}'))

    bot.edit_message_text(f"Выберите права для {object_type} {object_name} в схеме {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Выбор прав для {object_type} {object_name} в схеме {schema_name}")

def toggle_permission(bot, call: CallbackQuery, schema_name: str, object_name: str, object_type: str, permission: str):
    '''Переключение прав (добавление/удаление) для указанного объекта'''
    key = f"{schema_name}|{object_name}"
    if key not in selected_permissions:
        selected_permissions[key] = set()

    if permission in selected_permissions[key]:
        selected_permissions[key].remove(permission)
    else:
        selected_permissions[key].add(permission)

    choose_permissions(bot, call, schema_name, object_name, object_type)

def edit_to_welcome(bot, message: Message):
    '''Возврат в главное меню с выбором схем'''
    schemas = get_schemas()

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema}') for schema in schemas]
    markup.add(*buttons)

    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))

    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Возврат в главное меню с выбором схем")

def delete_message(bot, message: Message):
    '''Удаление сообщения'''
    try:
        bot.delete_message(message.chat.id, message.message_id)
        logging.info(f"Удалено сообщение с id: {message.message_id}")
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения: {e}")

def close_connection(cursor, connection):
    '''Закрытие соединения с базой данных'''
    cursor.close()
    connection.close()
    logging.info("Соединение с базой данных закрыто")
