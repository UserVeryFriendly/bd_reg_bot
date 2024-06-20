from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import logging
from db_connection import connect_to_db
from db_gets import list_objects, get_schemas, get_users
from keyboard_markup import create_navigation_markup, create_user_navigation_markup
from redis_con import redis_client

connection, cursor = connect_to_db()

logging.basicConfig(level=logging.INFO)


def request_access(bot, message: Message):
    '''Показывает список схем для запроса доступа'''
    schema_ids = get_schemas()
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(schema, callback_data=f'schema_req|{schema_id}') for schema, schema_id in schema_ids.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("Назад", callback_data='back_main'))
    
    bot.edit_message_text("Выберите схему, к которой требуется доступ:", chat_id=message.chat.id, message_id=message.message_id, reply_markup=markup)
    logging.info("Показаны схемы для запроса доступа")


def show_schema_access_options(bot, message: Message, schema_id: str, call: CallbackQuery):
    '''Отображает опции для выбранной схемы'''
    schema_name = redis_client.get(schema_id)
    if schema_name:
        schema_name = schema_name.decode('utf-8')
    else:
        logging.error(f"Не удалось найти имя схемы по ключу: {schema_id}")
        bot.answer_callback_query(call.id, "Ошибка: схема не найдена.")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Доступ на схему", callback_data=f'grant_r|{schema_id}'))
    markup.add(InlineKeyboardButton("Посмотреть таблицы", callback_data=f'tables_r|{schema_id}|0'))
    markup.add(InlineKeyboardButton("Посмотреть вью", callback_data=f'views_r|{schema_id}|0'))
    markup.add(InlineKeyboardButton("Назад", callback_data='request_access'))

    bot.edit_message_text(f"Опции для схемы {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показаны опции для схемы {schema_name}")

def request_user_for_grant_r(bot, call: CallbackQuery, schema_id: str, page: int = 0):
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
    markup = create_navigation_markup(user_ids, callback_prefix, schema_id, page, ad_pref='_r')

    bot.edit_message_text(f"Выберите пользователя для выдачи прав на схему {schema_name}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    logging.info(f"Показан список пользователей для схемы {schema_name}, страница {page}")