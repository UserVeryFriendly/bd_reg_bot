from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from telebot import types
import logging
from db_connection import connect_to_db
from db_gets import list_objects, get_schemas, get_users # noqa
from keyboard_markup import create_navigation_markup, create_user_navigation_markup
from redis_con import redis_client
import csv


connection, cursor = connect_to_db()

logging.basicConfig(level=logging.INFO)


def load_authorized_admin(filepath='authorized_admin.csv'):
    authorized_admin_ids = []
    with open(filepath, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            authorized_admin_ids.append(int(row['user_id']))
    return authorized_admin_ids


def load_authorized_user(filepath='authorized_user.csv'):
    authorized_user_ids = []
    with open(filepath, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            authorized_user_ids.append(int(row['user_id']))
    return authorized_user_ids


AUTHORIZED_ADMIN_IDS = load_authorized_admin()
AUTHORIZED_USER_IDS = load_authorized_user()


def is_admin(user_id):
    return user_id in AUTHORIZED_ADMIN_IDS


def is_user(user_id):
    return user_id in AUTHORIZED_USER_IDS or is_admin(user_id)

# ===================== Функции взаимодействия с пользователем =====================


def send_welcome(bot, user_id, chat_id):
    '''Отправляет приветственное сообщение'''

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keys = [key.decode('utf-8') for key in redis_client.keys('req*')]
    if is_admin(user_id):
        buttons = [
            types.InlineKeyboardButton(text='Выдать доступ', callback_data='admin_menu'),
            types.InlineKeyboardButton(text=f'Запросы доступа: {len(keys)}', callback_data='user_requests')
        ]
        keyboard.add(*buttons)
    else:
        print(user_id)

    keyboard.add(types.InlineKeyboardButton(text='Получить доступ', callback_data='request_access'))

    bot.send_message(chat_id, "Добро пожаловать! Выберите нужный раздел:", reply_markup=keyboard)
    logging.info("Отправлено начальное сообщение с выбором функций")


def show_admin_menu(bot, message: Message):
    schema_ids = get_schemas()

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema_id}') for schema, schema_id in schema_ids.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))

    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Показано административное меню с выбором схем")


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

    user_ids = {user: f'u{idx}' for idx, user in enumerate(users)}
    for user_name, user_id in user_ids.items():
        redis_client.set(user_id, user_name)

    logging.info("Сохранены имена пользователелей в Redis.")
    callback_prefix = 'choose_perm'
    # logging.info(f"Вызов функции create_navigation_markup в request_user_for_grant с user_ids: {user_ids}, callback_prefix: {callback_prefix}, schema_id: {schema_id}, page: {page}")
    markup, ad_pref = create_navigation_markup(user_ids, callback_prefix, schema_id, page)

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показан список пользователей для схемы {schema_name}, страница {page}")


def grant_usage_to_schema(bot, call: CallbackQuery, schema_id: str, user_id: str, permission_type: str):
    '''Выдаёт права на использование или создание объектов в схеме'''
    try:
        logging.info(f"Получение имени схемы по ключу: {schema_id} из Redis.")
        schema_name = redis_client.get(schema_id)
        if schema_name:
            schema_name = schema_name.decode('utf-8')
            logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя схемы по ключу: {schema_id} из Redis.")
            bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
            return

        logging.info(f"Получение имени пользователя по ключу: {user_id} из Redis.")
        user_name = redis_client.get(user_id)
        if user_name:
            user_name = user_name.decode('utf-8')
            logging.info(f"Считано имя пользователя: {user_name} по user_id: {user_id} из Redis.")
        else:
            logging.error(f"Не удалось найти имя пользователя по ключу: {user_id} из Redis.")
            bot.answer_callback_query(call.id, "Ошибка: пользователь не найден.")
            return

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


def choose_permission(bot, call: CallbackQuery, schema_id: str, user_id: str, ad_pref=''):
    '''Запрашивает тип прав для пользователя на схему'''

    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
        logging.info(f"Считано имя схемы: {schema_name} по schema_id: {schema_id} из Redis.")
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id} из Redis.")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

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


def save_permission_request_to_redis(permission_type, schema_id, user_id):
    '''Сохранение запроса на предоставление прав к схеме в Redis'''
    try:
        schema_name = redis_client.get(schema_id)
        user_name = redis_client.get(user_id)

        if not schema_name:
            logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
            return False

        schema_name = schema_name.decode('utf-8')

        if not user_name:
            logging.error(f"Не удалось найти имя пользователя по ключу: {user_id}")
            return False

        user_name = user_name.decode('utf-8')

        idx = 0
        while True:
            req_id = f'req{idx}'
            if not redis_client.exists(req_id):
                break
            idx += 1

        if permission_type == 'usage':
            sql_query = f"GRANT USAGE ON SCHEMA {schema_name} TO {user_name}"
        elif permission_type == 'create_usage':
            sql_query = f"GRANT USAGE, CREATE ON SCHEMA {schema_name} TO {user_name}"

        redis_client.set(req_id, sql_query)
        logging.info(f"Сохранён запрос: {sql_query} с ключом {req_id} в Redis.")
        return True

    except Exception as e:
        logging.error(f"Произошла ошибка при сохранении запроса: {e}")
        return False


def save_object_permission_request_to_redis(schema_id, object_id, user_id, object_type):
    '''Сохранение запроса на предоставление прав в Redis'''
    try:
        schema_name = redis_client.get(schema_id)
        user_name = redis_client.get(user_id)
        object_name = redis_client.get(object_id)

        if not schema_name:
            logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
            return False

        schema_name = schema_name.decode('utf-8')

        if not user_name:
            logging.error(f"Не удалось найти имя пользователя по ключу: {user_id}")
            return False

        user_name = user_name.decode('utf-8')

        if not object_name:
            logging.error(f"Не удалось найти имя объекта по ключу: {object_id}")
            return False

        object_name = object_name.decode('utf-8')

        key = f"{schema_name}|{object_name}"
        permissions = selected_permissions.get(key, set())
        if not permissions:
            logging.error(f"Не выбрано ни одного права для {object_type} {object_name}.")
            return False

        permissions_str = ', '.join(permissions)

        prefix = 'req'
        idx = 0
        while True:
            req_id = f'{prefix}{idx}'
            if not redis_client.exists(req_id):
                break
            idx += 1

        sql_query = f"GRANT {permissions_str} ON {object_type.upper()} {schema_name}.{object_name} TO {user_name}"

        redis_client.set(req_id, sql_query)
        logging.info(f"Сохранён запрос: {sql_query} с ключом {req_id} в Redis.")
        return True
    except Exception as e:
        logging.error(f"Произошла ошибка при сохранении запроса: {e}")
        return False


def edit_to_welcome(bot, message: Message):
    '''Возврат в главное меню с выбором схем'''
    schema_ids = get_schemas()

    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema|{schema_id}') for schema, schema_id in schema_ids.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))

    bot.edit_message_text("Выберите схему:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Показано административное меню с выбором схем")


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


def show_requests(bot, message, page: int = 0, query_or_message=None):
    """Показывает запросы на доступ, постранично."""
    keys = [key.decode('utf-8') for key in redis_client.keys('req*')]
    keys.sort()

    start_idx = page * 10
    end_idx = start_idx + 10
    requests_on_page = keys[start_idx:end_idx]

    keyboard = []
    for key in requests_on_page:
        request_sql = redis_client.get(key).decode('utf-8')
        keyboard.append([InlineKeyboardButton(text=request_sql[:50] + '...', callback_data=f'show_request|{key}')])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая страница", callback_data=f'nav_requests|{page - 1}'))
    if end_idx < len(keys):
        nav_buttons.append(InlineKeyboardButton("Следующая страница ➡️", callback_data=f'nav_requests|{page + 1}'))

    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("Выйти", callback_data='back_main')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if query_or_message:
        bot.edit_message_reply_markup(chat_id=query_or_message.message.chat.id, message_id=query_or_message.message.message_id, reply_markup=reply_markup)
    else:
        bot.send_message(message.chat.id, f'Запросы на доступ (страница {page + 1}):', reply_markup=reply_markup)


def show_user_requests_menu(bot, message):
    """Показывает меню запросов на доступ по пользователям."""
    keys = [key.decode('utf-8') for key in redis_client.keys('req*')]
    users = {}

    for key in keys:
        request_sql = redis_client.get(key).decode('utf-8')
        user_name = request_sql.split("TO ")[-1]
        if user_name not in users:
            users[user_name] = []
        users[user_name].append(key)

    keyboard = []
    for user_name in users:
        keyboard.append([InlineKeyboardButton(text=user_name, callback_data=f'show_user_requests|{user_name}')])

    keyboard.append([InlineKeyboardButton("Выйти", callback_data='back_main')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text('Запросы на доступ:', chat_id=message.chat.id, message_id=message.message_id, reply_markup=reply_markup)


def show_requests_for_user(bot, call, user_name):
    """Показывает запросы на доступ для конкретного пользователя."""
    filtered_requests = [
        (key.decode('utf-8'), redis_client.get(key).decode('utf-8'))
        for key in redis_client.keys('req*')
        if f"TO {user_name}" in redis_client.get(key).decode('utf-8')
    ]

    keyboard = []
    for req_key, request_sql in filtered_requests:
        request_info = format_request_info(request_sql)
        keyboard.append([InlineKeyboardButton(text=request_info, callback_data=f'query|{req_key}')])

    keyboard.append([InlineKeyboardButton("Выйти", callback_data='back_main')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(f'Запросы для {user_name}:', chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=reply_markup)


def format_request_info(request_sql):
    """Возвращает краткую информацию о запросе в удобочитаемом формате."""
    if "ON SCHEMA" in request_sql:
        schema_name = request_sql.split("ON SCHEMA")[1].split()[0]
        permissions = request_sql.split("GRANT")[1].split("ON SCHEMA")[0].strip()
        return f"{permissions} to {schema_name}"
    elif "ON TABLE" in request_sql:
        table_name = request_sql.split("ON TABLE")[1].split()[0]
        permissions = request_sql.split("GRANT")[1].split("ON TABLE")[0].strip()
        return f"{permissions} to {table_name}"
    return "Неизвестный тип запроса"


def display_request(bot, call: CallbackQuery, request_key):
    """Отображает SQL запрос и кнопки для его подтверждения или отказа."""
    request_sql = redis_client.get(request_key).decode('utf-8')

    keyboard = [[
        InlineKeyboardButton("Принять", callback_data=f'accept|{request_key}'),
        InlineKeyboardButton("Отказать", callback_data=f'decline|{request_key}')
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(text=f"Запрос:\n{request_sql}",
                          chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=reply_markup)


def execute_and_delete_request(bot, call: CallbackQuery, request_key, accept):
    """Выполняет или отменяет запрос на основе выбора пользователя."""
    request_sql = redis_client.get(request_key).decode('utf-8')

    if accept:
        try:
            cursor.execute(request_sql)
            connection.commit()
            response_message = "Запрос был успешно выполнен."
            logging.info(f"{request_sql} был выполнен")

        except Exception as e:
            response_message = f"Ошибка при выполнении запроса: {e}"
    else:
        response_message = "Запрос был отклонён."

    redis_client.delete(request_key)
    logging.info(f"Запрос {request_key} был удален из redis")
    bot.answer_callback_query(call.id, response_message)
    # bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    show_user_requests_menu(bot, call.message)
