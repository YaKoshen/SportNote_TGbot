import logging

from environs import Env


env = Env()
env.read_env()


class Config:
    WEBSITE_URL = env("WEBSITE_URL")
    UPDATES_RECEIVE_FREQUENCY = env.int("UPDATES_RECEIVE_FREQUENCY", 3)
    PING_FREQUENCY = env.int("PING_FREQUENCY")  # раз в сколько секунд мы дергает сайт на доступность
    BOT_TOKEN = env("BOT_TOKEN")
    CHATS_LIST_FILE_NAME = env("CHATS_LIST_FILE_NAME", "chats.txt")
    CURRENT_UPDATE_ID_FILE_NAME = env("CURRENT_UPDATE_ID_FILE_NAME", "current_update_id.txt")
    RESOURCE_NAME = env("RESOURCE_NAME")

    LOGGING_FORMAT_DEBUG = "%(asctime)s [%(levelname)s]: %(name)s.%(funcName)s: line %(lineno)d: %(message)s"
    LOGGING_FORMAT_INFO = "%(asctime)s [%(levelname)s]: %(message)s"
    DEBUG = env.bool("DEBUG", True)
    LOGGING_LEVEL = (logging.INFO, logging.DEBUG)[DEBUG]
