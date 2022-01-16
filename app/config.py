from environs import Env


env = Env()
env.read_env()


class Config:
    WEBSITE_URL = env("WEBSITE_URL")
    PING_FREQUENCY = env.int("PING_FREQUENCY")  # раз в сколько секунд мы дергает сайт на доступность
    BOT_TOKEN = env("BOT_TOKEN")
    CHATS_LIST_FILE_NAME = env("CHATS_LIST_FILE_NAME", "chats.txt")
    CURRENT_UPDATE_ID_FILE_NAME = env("CURRENT_UPDATE_ID_FILE_NAME", "current_update_id.txt")
