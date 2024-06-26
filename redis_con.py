import configparser
import redis

config = configparser.ConfigParser()
config.read('D:/GH/nguk/config/global_config.cfg')


def connect_to_redis():
    redis_params = {
        'host': str(config['REDIS']['host']),
        'port': int(config['REDIS']['port']),
        'db': int(config['REDIS']['db']),
        'password': str(config['REDIS']['password']) if config['REDIS']['password'] else None
    }
    return redis.StrictRedis(**redis_params)


redis_client = connect_to_redis()
