import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db_connection import connect_to_db
from keyboard_markup import create_navigation_markup

connection, cursor = connect_to_db()

def get_objects(schema_name, object_type):
    if object_type == 'tables':
        query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}' AND table_type = 'BASE TABLE' ORDER BY table_name"
    elif object_type == 'views':
        query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}' AND table_type = 'VIEW' ORDER BY table_name"
    cursor.execute(query)
    objects = [row['table_name'] for row in cursor.fetchall()]
    logging.info(f"Схема {schema_name} содержит {len(objects)} {object_type}.")
    return objects

def list_objects(bot, message, schema_name, page, call, object_type):
    logging.info(f"Запрашиваем {object_type} для схемы: {schema_name}, страница: {page}")

    objects = get_objects(schema_name, object_type)
    logging.info(f"Количество {object_type}: {len(objects)}")

    if not objects:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Назад", callback_data=f'back|{schema_name}'))
        bot.edit_message_text(f"В схеме {schema_name} нет {object_type}.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        logging.info(f"В схеме {schema_name} нет {object_type}.")
        return

    callback_prefix = f'choose_{object_type[:-1]}'
    markup = create_navigation_markup(objects, callback_prefix, schema_name, page)

    bot.edit_message_text(f"{object_type.capitalize()} в схеме {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показаны {object_type} в схеме {schema_name} для страницы {page}")

def get_schemas():
    cursor.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            AND schema_name NOT LIKE 'pg_%'
        ORDER BY schema_name;
    """)
    schemas = [row['schema_name'] for row in cursor.fetchall()]
    return schemas

def get_users():
    '''Получает список пользователей из базы данных'''
    cursor.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin = TRUE ORDER BY rolname")
    users = [row['rolname'] for row in cursor.fetchall()]
    logging.info(f"Получено {len(users)} пользователей.")
    return users