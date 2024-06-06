from telebot.types import CallbackQuery
import logging
from bot_main import (
    show_admin_menu, request_access, show_schema_options, 
    request_user_for_grant, choose_permission, 
    grant_usage_to_schema, list_objects, 
    choose_permissions, toggle_permission,
    request_user_for_permissions, grant_permissions, 
    delete_message, edit_to_welcome, send_welcome
)

def callback_inline(bot, call: CallbackQuery):
    try:
        logging.info(f"Получен вызов с данными: {call.data}")

        if call.data == 'admin_menu':
            show_admin_menu(bot, call.message)
        elif call.data == 'request_access':
            request_access(bot, call.message)
        elif call.data == 'back_main':
            delete_message(bot, call.message)
            send_welcome(bot, call.message)
        elif call.data.startswith('schema|'):
            schema_name = call.data.split('|')[1]
            show_schema_options(bot, call.message, schema_name, call)
        elif call.data.startswith('grant|'):
            schema_name = call.data.split('|')[1]
            request_user_for_grant(bot, call, schema_name)
        elif call.data.startswith('choose_perm|'):
            parts = call.data.split('|')
            if len(parts) == 3:
                schema_name = parts[1]
                user_to_grant = parts[2]
                choose_permission(bot, call, schema_name, user_to_grant)
        elif call.data.startswith('grant_permission|'):
            parts = call.data.split('|')
            if len(parts) == 4:
                permission_type = parts[1]
                schema_name = parts[2]
                user_to_grant = parts[3]
                grant_usage_to_schema(bot, call, schema_name, user_to_grant, permission_type)
        elif call.data.startswith('tables|') or call.data.startswith('views|'):
            parts = call.data.split('|')
            if len(parts) == 3:
                schema_name = parts[1]
                page = int(parts[2])
                object_type = 'tables' if call.data.startswith('tables|') else 'views'
                list_objects(bot, call.message, schema_name, page, call, object_type)
        elif call.data.startswith('choose_table|') or call.data.startswith('choose_view|'):
            parts = call.data.split('|')
            if len(parts) == 3:
                schema_name = parts[1]
                object_name = parts[2]
                object_type = 'table' if 'choose_table' in call.data else 'view'
                choose_permissions(bot, call, schema_name, object_name, object_type)
        elif call.data.startswith('toggle_perm|'):
            parts = call.data.split('|')
            if len(parts) == 5:
                schema_name = parts[1]
                object_name = parts[2]
                object_type = parts[3]
                permission = parts[4]
                toggle_permission(bot, call, schema_name, object_name, object_type, permission)
        elif call.data.startswith('choose_user|'):
            parts = call.data.split('|')
            if len(parts) == 4:
                schema_name = parts[1]
                object_name = parts[2]
                object_type = parts[3]
                request_user_for_permissions(bot, call, schema_name, object_name, object_type)
        elif call.data.startswith('grant_table_perm|') or call.data.startswith('grant_view_perm|'):
            parts = call.data.split('|')
            if len(parts) == 4:
                schema_name = parts[1]
                object_name = parts[2]
                user_to_grant = parts[3]
                object_type = 'table' if 'grant_table_perm' in call.data else 'view'
                grant_permissions(bot, call, schema_name, object_name, user_to_grant, object_type)
        elif call.data.startswith('prev_user_perm|') or call.data.startswith('next_user_perm|'):
            parts = call.data.split('|')
            if len(parts) == 5:
                schema_name = parts[1]
                object_name = parts[2]
                object_type = parts[3]
                page = int(parts[4])
                request_user_for_permissions(bot, call, schema_name, object_name, object_type, page)
        elif call.data.startswith('prev_users|') or call.data.startswith('next_users|'):
            parts = call.data.split('|')
            if len(parts) == 3:
                schema_name = parts[1]
                page = int(parts[2])
                request_user_for_grant(bot, call, schema_name, page)
        elif call.data == 'back_main':
            delete_message(bot, call.message)
            send_welcome(bot, call.message)
        elif call.data.startswith('back|'):
            schema_name = call.data.split('|')[1]
            show_schema_options(bot, call.message, schema_name, call)
        elif call.data.startswith('choose_table_prev|') or call.data.startswith('choose_table_next|') or \
             call.data.startswith('choose_view_prev|') or call.data.startswith('choose_view_next|'):
            logging.info(f"Обрабатываем кнопку пагинации: {call.data}")
            parts = call.data.split('|')
            if len(parts) == 3:
                schema_name = parts[1]
                page = int(parts[2])
                object_type = 'tables' if 'choose_table' in call.data else 'views'
                list_objects(bot, call.message, schema_name, page, call, object_type)
    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")