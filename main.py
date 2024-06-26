import telebot
from telebot.types import Message
import configparser
import logging
from bot_admin import send_welcome, close_connection
from callback_handler import callback_inline
from db_connection import connect_to_db

logging.basicConfig(level=logging.INFO)

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')

TELEGRAM_TOKEN = config['TOKEN']['test_try']  # Пример: @MyFirstTestTry_bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

connection, cursor = connect_to_db()


@bot.message_handler(commands=['start'])
def start_message(message: Message):
    send_welcome(bot, message)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    callback_inline(bot, call)


try:
    bot.polling(none_stop=True)
except KeyboardInterrupt:
    close_connection(cursor, connection)
    logging.info("Остановка бота")
