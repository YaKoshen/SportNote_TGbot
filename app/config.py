import logging

from environs import Env


env = Env()
env.read_env()


class Config:
    WEBSITE_URL = env("WEBSITE_URL")
    PING_FREQUENCY = env.int("PING_FREQUENCY")  # раз в сколько секунд мы дергает сайт на доступность
    WEBSITE_DOWN_SLEEP_TIME = env.int("WEBSITE_DOWN_SLEEP_TIME", 5)  # как часто посылаем оповещения если сайт лежит
    WEBSITE_UP_SLEEP_TIME = env.int("WEBSITE_UP_SLEEP_TIME", 300)  # как часто посылаем оповещения если сайт работает

    UPDATES_RECEIVE_FREQUENCY = env.int("UPDATES_RECEIVE_FREQUENCY", 3)  # как часто дергаем тг на апдейты
    BOT_TOKEN = env("BOT_TOKEN")
    RECONNECT_TO_TG_SLEEP_TIME = env.float("RECONNECT_TO_TG_SLEEP_TIME", 60)

    with env.prefixed('DATABASE_'):
        DATABASE_URI = env('URI', '') or 'postgres://{user}:{password}@{host}:{port}/{database}'.format(
            user=env('USER'),
            password=env('PASSWORD'),
            host=env('HOST'),
            port=env('PORT', 5432),
            database=env('NAME'),
        )

    USERS_STORAGE_DIRECTORY = env("USERS_STORAGE_DIRECTORY")

    CURRENT_UPDATE_ID_FILE_NAME = env("CURRENT_UPDATE_ID_FILE_NAME", "current_update_id.txt")
    RESOURCE_NAME = env("RESOURCE_NAME")

    LOGGING_FORMAT_DEBUG = "%(asctime)s [%(levelname)s]: %(name)s.%(funcName)s: line %(lineno)d: %(message)s"
    LOGGING_FORMAT_INFO = "%(asctime)s [%(levelname)s]: %(message)s"
    DEBUG = env.bool("DEBUG", True)
    LOGGING_LEVEL = (logging.INFO, logging.DEBUG)[DEBUG]
