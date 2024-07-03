import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db_connection import connect_to_db
from keyboard_markup import create_navigation_markup, page_size
from redis_con import redis_client

connection, cursor = connect_to_db()


def get_objects(schema_name, object_type):
    if object_type == 'tables':
        query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE' ORDER BY table_name"
    elif object_type == 'views':
        query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}' AND table_type = 'VIEW' ORDER BY table_name"

    cursor.execute(query)
    objects = [row[0] for row in cursor.fetchall()]
    logging.info(f"Схема {schema_name} содержит {len(objects)} {object_type}.")

    object_ids = {}
    prefix = 't' if object_type == 'tables' else 'w'
    idx = 0

    for obj in objects:
        while True:
            object_id = f'{prefix}{idx}'
            if not redis_client.exists(object_id):
                redis_client.set(object_id, obj)
                break
            else:
                existing_value = redis_client.get(object_id)
                if existing_value and existing_value.decode('utf-8') == obj:
                    break
            idx += 1

        object_ids[obj] = object_id
    logging.info("Взаимодействие с Redis окончено")
    return object_ids


def list_objects(bot, message, schema_id, page, call, object_type, ad_pref=''):
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    logging.info(f"Запрашиваем {object_type} для схемы: {schema_name}, страница: {page}")

    object_ids = get_objects(schema_name, object_type)
    logging.info(f"Количество {object_type}: {len(object_ids)}")

    if not object_ids:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Назад", callback_data=f'back{ad_pref}|{schema_id}'))
        bot.edit_message_text(f"В схеме {schema_name} нет {object_type}.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        logging.info(f"В схеме {schema_name} нет {object_type}.")
        return

    total_pages = (len(object_ids) + page_size - 1) // page_size
    callback_prefix = f'choose_{object_type[:-1]}'
    markup, ad_pref = create_navigation_markup(object_ids, callback_prefix, schema_id, page, ad_pref)

    bot.edit_message_text(f"{object_type.capitalize()} в схеме {schema_name} ({page + 1}/{total_pages}):", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показаны {object_type} в схеме {schema_name} для страницы {page}")


def get_schemas():
    cursor.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            AND schema_name NOT LIKE 'pg_%'
        ORDER BY schema_name;
    """)

    schemas = [row[0] for row in cursor.fetchall()]

    schema_ids = {}
    idx = 0

    for schema in schemas:
        while True:
            schema_id = f's{idx}'
            if not redis_client.exists(schema_id):
                redis_client.set(schema_id, schema)
                break
            else:
                existing_value = redis_client.get(schema_id)
                if existing_value and existing_value.decode('utf-8') == schema:
                    break
            idx += 1

        schema_ids[schema] = schema_id
    logging.info("Взаимодействие с Redis окончено")
    return schema_ids


def get_users():
    '''Получает список пользователей из базы данных'''
    cursor.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin = TRUE ORDER BY rolname")
    users = [row['rolname'] for row in cursor.fetchall()]
    logging.info(f"Получено {len(users)} пользователей.")
    return users
