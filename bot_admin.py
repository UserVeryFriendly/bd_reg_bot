from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import logging
from db_connection import connect_to_db
from db_gets import list_objects, get_schemas, get_users
from keyboard_markup import create_navigation_markup, create_user_navigation_markup
from redis_con import redis_client

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

def show_admin_menu(bot, message: Message):
    schema_ids = get_schemas()
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema_id}') for schema, schema_id in schema_ids.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))
    
    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info(f"Показано административное меню с выбором схем")

def show_schema_options(bot, message: Message, schema_id: str, call: CallbackQuery):
    '''Отображает опции для выбранной схемы'''
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Выдать права", callback_data=f'grant|{schema_id}'))
    markup.add(InlineKeyboardButton("Посмотреть таблицы", callback_data=f'tables|{schema_id}|0'))
    markup.add(InlineKeyboardButton("Посмотреть вью", callback_data=f'views|{schema_id}|0'))
    markup.add(InlineKeyboardButton("Назад", callback_data='admin_menu'))

    bot.edit_message_text(f"Опции для схемы {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показаны опции для схемы {schema_name}")


# ===================== Функции работы с пользовательскими правами =====================
def choose_user(bot, call: CallbackQuery, schema_id: str, object_id: str, object_type: str, ad_pref=''):
    '''Выбор пользователя для указанного объекта'''

    logging.info(f"Получен вызов choose_user с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}")

    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
        logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}.")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return
    
    object_name = redis_client.get(object_id)
    if object_name:
        object_name = object_name.decode('utf-8')
        logging.info(f"Считано имя объекта: {object_name} по object_id: {object_id} из Redis.")
    else:
        logging.error(f"Не удалось найти объект по ключу: {object_id}.")
        bot.answer_callback_query(call.id, "Ошибка: объект не найден.")
        return

    request_user_for_permissions(bot, call, schema_id, object_id, object_type, ad_pref=ad_pref)


def request_user_for_permissions(bot, call: CallbackQuery, schema_id: str, object_id: str, object_type: str, page: int = 0, ad_pref=''):
    '''Запрашивает пользователя для выдачи прав на указанный объект'''
    
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
        logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}.")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    object_name = redis_client.get(object_id)
    if object_name:
        object_name = object_name.decode('utf-8')
        logging.info(f"Считано имя объекта: {object_name} по object_id: {object_id} из Redis.")
    else:
        logging.error(f"Не удалось найти объект по ключу: {object_id}.")
        bot.answer_callback_query(call.id, "Ошибка: объект не найден.")
        return

    users = get_users()
    if not users:
        bot.send_message(call.message.chat.id, "Нет доступных пользователей для выдачи прав.")
        logging.info("Нет доступных пользователей для выдачи прав.")
        return

    # Приведение списка пользователей к словарю
    user_ids = {user: f"u{idx}" for idx, user in enumerate(users)}
    for user_name, user_id in user_ids.items():
        redis_client.set(user_id, user_name)        

    callback_prefix = f"grant_{object_type}_perm"
    # logging.info(f"Вызов функции create_navigation_markup в request_user_for_permissions с user_ids: {user_ids}, callback_prefix: {callback_prefix}, schema_id: {schema_id}, page: {page}")
    markup = create_user_navigation_markup(user_ids, callback_prefix, schema_id, object_id, object_type, page, ad_pref)

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на {object_type} {object_name} в схеме {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Выбор пользователя для выдачи прав на {object_type} {object_name} в схеме {schema_name}, страница {page}")

def grant_permissions(bot, call: CallbackQuery, schema_id: str, object_id: str, user_id: str, object_type: str):
    '''Выдаёт права на указанный объект пользователю'''
    try:
        logging.info(f"Выдача прав пользователю с id {user_id} на {object_type} с id {object_id} в схеме с id {schema_id}")

        # Получаем имя схемы по её id
        schema_name = redis_client.get(schema_id)
        if schema_name:
            schema_name = schema_name.decode('utf-8')
            logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}.")
            bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
            return

        # Получаем имя объекта по его id
        object_name = redis_client.get(object_id)
        if object_name:
            object_name = object_name.decode('utf-8')
            logging.info(f"Считано имя объекта: {object_name} по object_id: {object_id} из Redis.")
        else:
            logging.error(f"Не удалось найти объект по ключу: {object_id}.")
            bot.answer_callback_query(call.id, "Ошибка: объект не найден.")
            return

        # Получаем имя пользователя по его id
        user_name = redis_client.get(user_id)
        if user_name:
            user_name = user_name.decode('utf-8')
            logging.info(f"Считано имя пользователя: {user_name} по user_id: {user_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя пользователя по ключу: {user_id}.")
            bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
            return

        key = f"{schema_name}|{object_name}"
        permissions = selected_permissions.get(key, set())
        if not permissions:
            bot.answer_callback_query(call.id, text=f"Не выбрано ни одного права для {object_type} {object_name}.")
            return

        permissions_str = ', '.join(permissions)
        cursor.execute(f"GRANT {permissions_str} ON TABLE {schema_name}.{object_name} TO {user_name}")

        connection.commit()

        bot.answer_callback_query(call.id, text=f"Выданы права ({permissions_str}) на {object_type} {object_name} пользователю {user_name}.")
        logging.info(f"Права ({permissions_str}) на {object_type} {object_name} выданы для пользователя {user_name}")

        selected_permissions.pop(key, None)

    except Exception as e:
        bot.answer_callback_query(call.id, text=f"Ошибка при выдаче прав: {e}")
        logging.error(f"Ошибка при выдаче прав: {e}")

    edit_to_welcome(bot, call.message)


def request_user_for_grant(bot, call: CallbackQuery, schema_id: str, page: int = 0):
    '''Запрашивает пользователя для выдачи прав на схему'''
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
        logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id} из Redis.")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    users = get_users()
    if not users:
        bot.send_message(call.message.chat.id, "Нет доступных пользователей для выдачи прав.")
        logging.info("Нет доступных пользователей для выдачи прав.")
        return

    # Конвертируем список пользователей в словарь и сохраняем в Redis
    user_ids = {user: f'u{idx}' for idx, user in enumerate(users)}
    for user_name, user_id in user_ids.items():
        redis_client.set(user_id, user_name)

    logging.info(f"Сохранены имена пользователелей в Redis.")
    callback_prefix = 'choose_perm'
    # logging.info(f"Вызов функции create_navigation_markup в request_user_for_grant с user_ids: {user_ids}, callback_prefix: {callback_prefix}, schema_id: {schema_id}, page: {page}")
    markup = create_navigation_markup(user_ids, callback_prefix, schema_id, page)

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показан список пользователей для схемы {schema_name}, страница {page}")


def grant_usage_to_schema(bot, call: CallbackQuery, schema_id: str, user_id: str, permission_type: str):
    '''Выдаёт права на использование или создание объектов в схеме'''
    try:
        logging.info(f"Получение имени схемы по ключу: {schema_id} из Redis.")
        # Получаем имя схемы по её id
        schema_name = redis_client.get(schema_id)
        if schema_name:
            schema_name = schema_name.decode('utf-8')
            logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя схемы по ключу: {schema_id} из Redis.")
            bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
            return

        logging.info(f"Получение имени пользователя по ключу: {user_id} из Redis.")
        # Получаем имя пользователя по его id
        user_name = redis_client.get(user_id)
        if user_name:
            user_name = user_name.decode('utf-8')
            logging.info(f"Считано имя пользователя: {user_name} по user_id: {user_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя пользователя по ключу: {user_id} из Redis.")
            bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
            return

        # Выполняем SQL запрос на выдачу прав
        if permission_type == 'usage':
            cursor.execute(f"GRANT USAGE ON SCHEMA {schema_name} TO {user_name}")
        elif permission_type == 'create_usage':
            cursor.execute(f"GRANT USAGE, CREATE ON SCHEMA {schema_name} TO {user_name}")

        connection.commit()
        bot.answer_callback_query(call.id, text=f"Выдано право на {permission_type} схемы {schema_name} пользователю {user_name}")
        logging.info(f"Права на {permission_type} схемы {schema_name} выданы для пользователя {user_name}")
    except Exception as e:
        bot.answer_callback_query(call.id, text=f"Ошибка при выдаче прав: {e}")
        logging.error(f"Ошибка при выдаче прав: {e}")

    edit_to_welcome(bot, call.message)


def choose_permission(bot, call: CallbackQuery, schema_id: str, user_id: str, ad_pref = ''):
    '''Запрашивает тип прав для пользователя на схему'''

    # Получаем имя схемы по её id
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
        logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id} из Redis.")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    # Получаем имя пользователя по его id
    user_name = redis_client.get(user_id)
    if user_name:
        user_name = user_name.decode('utf-8')
        logging.info(f"Считано имя пользователя: {user_name} по user_id: {user_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя пользователя по ключу: {user_id} из Redis.")
        bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Usage", callback_data=f'grant_permission{ad_pref}|usage|{schema_id}|{user_id}'))
    markup.add(InlineKeyboardButton("Create + Usage", callback_data=f'grant_permission{ad_pref}|create_usage|{schema_id}|{user_id}'))
    markup.add(InlineKeyboardButton("Назад", callback_data=f'grant{ad_pref}|{schema_id}'))  

    bot.edit_message_text(f"Выберите тип прав для пользователя {user_name} на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Нужен выбор типа прав для пользователя {user_name} на схему {schema_name}")

selected_permissions = {}

def choose_permissions(bot, call: CallbackQuery, schema_id: str, object_id: str, object_type: str, ad_pref=''):
    '''Выбор и отображение прав для указанного объекта'''

    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    object_name = redis_client.get(object_id)
    if object_name:
        object_name = object_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти объект по ключу: {object_id}")
        bot.answer_callback_query(call.id, "Ошибка: объект не найден.")
        return

    permissions = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER']
    key = f"{schema_name}|{object_name}"
    selected = selected_permissions.get(key, set())

    markup = InlineKeyboardMarkup()
    for perm in permissions:
        if perm in selected:
            markup.add(InlineKeyboardButton(f"{perm} ✅", callback_data=f"toggle_perm{ad_pref}|{schema_id}|{object_id}|{object_type}|{perm}"))
        else:
            markup.add(InlineKeyboardButton(perm, callback_data=f"toggle_perm{ad_pref}|{schema_id}|{object_id}|{object_type}|{perm}"))

    markup.add(InlineKeyboardButton("Выберите пользователя", callback_data=f"choose_user{ad_pref}|{schema_id}|{object_id}|{object_type}"))
    markup.add(InlineKeyboardButton("Назад", callback_data=f'back{ad_pref}|{schema_id}'))

    bot.edit_message_text(f"Выберите права для {object_type} {object_name} в схеме {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Выбор прав для {object_type} {object_name} в схеме {schema_name}")

def toggle_permission(bot, call: CallbackQuery, schema_id: str, object_id: str, object_type: str, permission: str, ad_pref=''):
    '''Переключение прав (добавление/удаление) для указанного объекта'''
    
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    object_name = redis_client.get(object_id)
    if object_name:
        object_name = object_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти объект по ключу: {object_id}")
        bot.answer_callback_query(call.id, "Ошибка: объект не найден.")
        return

    key = f"{schema_name}|{object_name}"
    if key not in selected_permissions:
        selected_permissions[key] = set()

    if permission in selected_permissions[key]:
        selected_permissions[key].remove(permission)
    else:
        selected_permissions[key].add(permission)

    choose_permissions(bot, call, schema_id, object_id, object_type, ad_pref=ad_pref)

    logging.info(f"Переключены права {permission} для {object_type} {object_name} в схеме {schema_name}")

def edit_to_welcome(bot, message: Message):
    '''Возврат в главное меню с выбором схем'''
    schema_ids = get_schemas()
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema_id}') for schema, schema_id in schema_ids.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))
    
    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info(f"Показано административное меню с выбором схем")

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
