from telebot.types import CallbackQuery, Message
# from redis_con import redis_client
import logging
import csv

# from redis_con import redis_client
from bot_admin import (
    show_admin_menu, show_schema_options,
    request_user_for_grant, choose_permission,
    grant_usage_to_schema, list_objects,
    choose_permissions, toggle_permission,
    request_user_for_permissions, grant_permissions,
    delete_message, send_welcome, choose_user,
    save_permission_request_to_redis,
    save_object_permission_request_to_redis,
    show_requests_for_user, show_user_requests_menu,
    display_request, execute_and_delete_request
)
from bot_access import (
    show_schema_access_options, request_access,
    request_user_for_grant_r
)


def load_authorized_users(filepath='authorized_users.csv'):
    authorized_user_ids = []
    with open(filepath, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            authorized_user_ids.append(int(row['user_id']))
    return authorized_user_ids


AUTHORIZED_USER_IDS = load_authorized_users()


def is_authorized(user_id):
    return user_id in AUTHORIZED_USER_IDS


def handle_req_command(bot, message: Message):
    """Обрабатывает команду /req, доступную только админам."""
    user_id = message.from_user.id
    if not is_authorized(user_id):
        bot.send_message(message.chat.id, "У вас нет прав на выполнение этой команды.")
        return

    # Показываем запросы с первой страницы
    show_user_requests_menu(bot, message)


def handle_callback_query(bot, call: CallbackQuery):
    """Обработчик инлайн-клавиатуры."""
    data = call.data
    parts = call.data.split('|')
    print(f'DATA: {data}')

    if data.startswith('show_user_requests|'):
        user_name = data.split('|')[1]
        show_requests_for_user(bot, call, user_name)

    elif data == 'exit_requests':
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)

    elif parts[0] == 'query':
        request_key = parts[1]
        display_request(bot, call, request_key)

    elif parts[0] == 'accept':
        request_key = parts[1]
        execute_and_delete_request(bot, call, request_key, accept=True)

    elif parts[0] == 'decline':
        request_key = parts[1]
        execute_and_delete_request(bot, call, request_key, accept=False)

    else:
        callback_inline(bot, call)


def callback_inline(bot, call: CallbackQuery):
    try:
        global parts
        ad_pref = '_r'
        parts = call.data.split('|')
        logging.info(f"Получен вызов с данными: {call.data}")
        logging.info(f"Части данных: {parts}")

        # ____АДМИНКА____
        # Блок обработки главного меню
        if call.data == 'admin_menu':
            if is_authorized(call.from_user.id):
                logging.info("_______▲▲▲_______Вызвана функция show_admin_menu_______▲▲▲_______")
                show_admin_menu(bot, call.message)
            else:
                bot.answer_callback_query(callback_query_id=call.id, text="У вас нет прав доступа к админке.", show_alert=True)
                logging.warning(f"Пользователь {call.from_user.id} не авторизован для доступа к админке")
        elif call.data == 'back_main':
            logging.info("_______▲▲▲_______Вызвана функция delete_message и send_welcome_______▲▲▲_______")
            delete_message(bot, call.message)
            send_welcome(bot, call.message)

        # Блок обработки схем
        elif parts[0] == 'schema':
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция show_schema_options с schema_id: {schema_id}_______▲▲▲_______")
                show_schema_options(bot, call.message, schema_id, call)

        # Блок обработки назначения прав
        elif parts[0] == 'grant':
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_grant с schema_id: {schema_id}_______▲▲▲_______")
                request_user_for_grant(bot, call, schema_id)
        elif parts[0] == 'choose_perm':
            if len(parts) == 3:
                schema_id = parts[1]
                user_id = parts[2]
                logging.info(f"_______▲▲▲_______Вызвана функция choose_permission с schema_id: {schema_id}, user_id: {user_id}_______▲▲▲_______")
                choose_permission(bot, call, schema_id, user_id)
        elif parts[0] == 'grant_permission':
            logging.info(f"Обработка grant_permission: parts = {parts}")
            if len(parts) == 4:
                permission_type = parts[1]
                schema_id = parts[2]
                user_id = parts[3]
                logging.info(f"_______▲▲▲_______Вызвана функция grant_usage_to_schema с schema_id: {schema_id}, user_id: {user_id}, permission_type: {permission_type}_______▲▲▲_______")
                grant_usage_to_schema(bot, call, schema_id, user_id, permission_type)

        # Блок обработки объектов
        elif parts[0] == 'tables' or parts[0] == 'views':
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                object_type = 'tables' if parts[0] == 'tables' else 'views'
                logging.info(f"_______▲▲▲_______Вызвана функция list_objects с schema_id: {schema_id}, page: {page}, object_type: {object_type}_______▲▲▲_______")
                list_objects(bot, call.message, schema_id, page, call, object_type)
        elif parts[0] == 'choose_table' or parts[0] == 'choose_view':
            if len(parts) == 3:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = 'table' if parts[0] == 'choose_table' else 'view'
                logging.info(f"_______▲▲▲_______Вызвана функция choose_permissions с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}_______▲▲▲_______")
                choose_permissions(bot, call, schema_id, object_id, object_type)

        # Блок переключения прав
        elif parts[0] == 'toggle_perm':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = parts[3]
                permission = parts[4]
                logging.info(f"_______▲▲▲_______Вызвана функция toggle_permission с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}, permission: {permission}_______▲▲▲_______")
                toggle_permission(bot, call, schema_id, object_id, object_type, permission)

        # Блок выбора пользователя
        elif parts[0] == 'choose_user':
            if len(parts) == 4:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = parts[3]
                logging.info(f"_______▲▲▲_______Вызвана функция choose_user с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}_______▲▲▲_______")
                choose_user(bot, call, schema_id, object_id, object_type)

        # Блок назначения прав пользователю для объекта
        elif parts[0] == 'grant_table_perm' or parts[0] == 'grant_view_perm':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                user_id = parts[3]
                object_type = parts[4]
                logging.info(f"_______▲▲▲_______Вызвана функция grant_permissions с schema_id: {schema_id}, object_id: {object_id}, user_id: {user_id}, object_type: {object_type}_______▲▲▲_______")
                grant_permissions(bot, call, schema_id, object_id, user_id, object_type)

        # Блок обработки пагинации для прав пользователя
        elif parts[0] == 'prev_user_perm' or parts[0] == 'next_user_perm':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = parts[3]
                page = int(parts[4])
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_permissions с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}, page: {page}_______▲▲▲_______")
                request_user_for_permissions(bot, call, schema_id, object_id, object_type, page)
        elif parts[0] == 'prev_users' or parts[0] == 'next_users':
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_grant с schema_id: {schema_id}, page: {page}_______▲▲▲_______")
                request_user_for_grant(bot, call, schema_id, page)

        # Блок возврата к предыдущему меню
        elif parts[0] == 'back':
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция show_schema_options с schema_id: {schema_id}_______▲▲▲_______")
                show_schema_options(bot, call.message, schema_id, call)

        # Блок обработки кнопок пагинации
        elif parts[0] == 'choose_table_prev' or parts[0] == 'choose_table_next' or \
                parts[0] == 'choose_view_prev' or parts[0] == 'choose_view_next':
            logging.info(f"Обрабатываем кнопку пагинации: {call.data}")
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                object_type = 'tables' if 'choose_table' in parts[0] else 'views'
                logging.info(f"_______▲▲▲_______Вызвана функция list_objects с schema_id: {schema_id}, page: {page}, object_type: {object_type}_______▲▲▲_______")
                list_objects(bot, call.message, schema_id, page, call, object_type)

        # Блок обработки дополнительной навигации для прав
        elif parts[0] == 'choose_perm_next' or parts[0] == 'choose_perm_prev':
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_grant с schema_id: {schema_id}, page: {page}_______▲▲▲_______")
                request_user_for_grant(bot, call, schema_id, page)

        elif parts[0] == 'grant_view_perm_next' or parts[0] == 'grant_view_perm_prev' or \
                parts[0] == 'grant_table_perm_next' or parts[0] == 'grant_table_perm_prev':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                page = int(parts[3])
                object_type = parts[4]
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_permissions с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}, page: {page}_______▲▲▲_______")
                request_user_for_permissions(bot, call, schema_id, object_id, object_type, page)

        # ____ЗАПРОС ПОЛЬЗОВАТЕЛЯ____
        # Во многих запросах передается ad_pref, нужен для обращения к тем же функциям, что пользуют админки, но немного разделить функционал в конце

        elif call.data == 'request_access':
            logging.info("_______▲▲▲_______Вызвана функция request_access_______▲▲▲_______")
            request_access(bot, call.message)

        elif call.data.startswith('schema_req|'):
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция show_schema_access_options с schema_id: {schema_id}_______▲▲▲_______")
                show_schema_access_options(bot, call.message, schema_id, call)

        elif parts[0] == 'grant_r':
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_grant_r с schema_id: {schema_id}_______▲▲▲_______")
                request_user_for_grant_r(bot, call, schema_id)

        elif parts[0] == 'choose_perm_r_next' or parts[0] == 'choose_perm_r_prev':
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                logging.info(f"_______▲▲▲_______Вызвана функция request_user_for_grant_r с schema_id: {schema_id}, page: {page}_______▲▲▲_______")
                request_user_for_grant_r(bot, call, schema_id, page)

        elif parts[0] == 'choose_perm_r':
            if len(parts) == 3:
                schema_id = parts[1]
                user_id = parts[2]
                logging.info(f"_______▲▲▲_______Вызвана функция choose_permission с schema_id: {schema_id}, user_id: {user_id}_______▲▲▲_______")
                choose_permission(bot, call, schema_id, user_id, ad_pref=ad_pref)

        elif parts[0] == 'grant_permission_r':
            logging.info(f"Обработка grant_permission_r: parts = {parts}")
            if len(parts) == 4:
                permission_type = parts[1]
                schema_id = parts[2]
                user_id = parts[3]
                save_permission_request_to_redis(permission_type, schema_id, user_id)
                logging.info(f"_______▲▲▲_______Вызвана функция save_permission_request_to_redis с schema_id: {schema_id} user_id: {user_id}_______▲▲▲_______")
                bot.answer_callback_query(call.id, "Запросы напрвален администратору")
                request_access(bot, call.message)

        elif parts[0] == 'tables_r' or parts[0] == 'views_r':
            if len(parts) == 3:
                schema_id = parts[1]
                page = int(parts[2])
                object_type = 'tables' if parts[0] == 'tables_r' else 'views'
                logging.info(f"_______▲▲▲_______Вызвана функция list_objects с schema_id: {schema_id}, page: {page}, object_type: {object_type}_______▲▲▲_______")
                list_objects(bot, call.message, schema_id, page, call, object_type, ad_pref=ad_pref)

        elif parts[0] == 'back_r':
            if len(parts) == 2:
                schema_id = parts[1]
                logging.info(f"_______▲▲▲_______Вызвана функция show_schema_access_options с schema_id: {schema_id}_______▲▲▲_______")
                show_schema_access_options(bot, call.message, schema_id, call)

        elif parts[0] == 'choose_table_r' or parts[0] == 'choose_view_r':
            if len(parts) == 3:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = 'table' if parts[0] == 'choose_table_r' else 'view'
                logging.info(f"_______▲▲▲_______Вызвана функция choose_permissions с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}_______▲▲▲_______")
                choose_permissions(bot, call, schema_id, object_id, object_type, ad_pref=ad_pref)

        elif parts[0] == 'toggle_perm_r':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = parts[3]
                permission = parts[4]
                logging.info(f"_______▲▲▲_______Вызвана функция toggle_permission с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}, permission: {permission}_______▲▲▲_______")
                toggle_permission(bot, call, schema_id, object_id, object_type, permission, ad_pref=ad_pref)

        elif parts[0] == 'choose_user_r':
            if len(parts) == 4:
                schema_id = parts[1]
                object_id = parts[2]
                object_type = parts[3]
                logging.info(f"_______▲▲▲_______Вызвана функция choose_user с schema_id: {schema_id}, object_id: {object_id}, object_type: {object_type}_______▲▲▲_______")
                choose_user(bot, call, schema_id, object_id, object_type, ad_pref=ad_pref)

        elif parts[0] == 'grant_table_perm_r' or parts[0] == 'grant_view_perm_r':
            if len(parts) == 5:
                schema_id = parts[1]
                object_id = parts[2]
                user_id = parts[3]
                object_type = parts[4]
                logging.info(f"_______▲▲▲_______Вызвана функция grant_permissions_r с schema_id: {schema_id}, object_id: {object_id}, user_id: {user_id}, object_type: {object_type}_______▲▲▲_______")
                save_object_permission_request_to_redis(schema_id, object_id, user_id, object_type)
                bot.answer_callback_query(call.id, "Запросы напрвален администратору")
                request_access(bot, call.message)

        else:
            handle_callback_query(bot, call)
    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
