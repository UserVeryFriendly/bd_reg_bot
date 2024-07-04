import telebot
from telebot.types import Message
import configparser
import logging
from bot_admin import send_welcome, close_connection
from callback_handler import callback_inline
from db_connection import connect_to_db
from redis_con import redis_client

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('config/config_file.cfg')

TELEGRAM_TOKEN = config['TOKEN']['bot_tok']  # Пример: @MyFirstTestTry_bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

connection, cursor = connect_to_db()


@bot.message_handler(commands=['start'])
def start_message(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    send_welcome(bot, user_id, chat_id)


@bot.message_handler(commands=['ref'])
def ref_command(message: Message):
    redis_client.flushall()
    bot.send_message(message.chat.id, 'Redis очищен')


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    callback_inline(bot, call)


try:
    bot.polling(none_stop=True)
except KeyboardInterrupt:
    close_connection(cursor, connection)
    logging.info("Остановка бота")
