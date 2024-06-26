import psycopg2
from psycopg2 import extras
import configparser

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')


def connect_to_db():
    db_params = {
        'host': str(config['RTK_DB']['host']),
        'port': int(config['RTK_DB']['port']),
        'database': str(config['RTK_DB']['database']),
        'user': str(config.get('RTK_DB', 'user')),
        'password': str(config['RTK_DB']['password']),
    }
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor(cursor_factory=extras.DictCursor)
    return connection, cursor
