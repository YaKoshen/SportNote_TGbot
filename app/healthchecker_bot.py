import asyncio
import os
import json

import aiohttp

from app.config import Config
from app.monitoring_resource import MonitoringResource
from app.utils import get_logger
from app.user_file_storing_model import User


class HealthcheckerBot:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.last_update_id = None
        self.__users = []
        self.monitoring_resource = MonitoringResource(name=Config.RESOURCE_NAME, url=Config.WEBSITE_URL)
        self.session = None

        self.__is_running = False  # работает ли бот в целом
        self.__is_receiving_updates = False  # получаем ли апдейты от тг
        self.__is_sending_notifications = False  # отсылаем ли инфо в фоновом режиме
        self.__is_monitoring = False  # посылает ли он запросы на сайт без исключений

    async def _on_start(self):
        self.logger.info("Starting...")

        # получаем id последнего обновления из файла
        self.logger.debug("Getting last update id from file: %s", Config.CURRENT_UPDATE_ID_FILE_NAME)

        if not os.path.exists(Config.CURRENT_UPDATE_ID_FILE_NAME):
            with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
                f.write(str(0))

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "r") as f:
            self.last_update_id = int(f.read().strip())

        self.logger.debug("Last update id got: %s", self.last_update_id)

        # получаем список всех чатов, куда нам надо отправлять оповещения
        self.logger.debug("Getting users we send messages to")

        if not os.path.exists(Config.USERS_STORAGE_DIRECTORY):
            os.mkdir(Config.USERS_STORAGE_DIRECTORY)

        for user_filename in os.listdir(Config.USERS_STORAGE_DIRECTORY):
            with open(os.path.join(Config.USERS_STORAGE_DIRECTORY, user_filename), "r") as user_file:
                self.__users.append(User.load(user_file))

        self.logger.debug("Users to send: %s", self.__users)

        self.session = aiohttp.ClientSession()
        self.logger.debug("Session created")

    async def _run(self):
        asyncio.ensure_future(self.receive_updates())
        asyncio.ensure_future(self.send_notifications())
        asyncio.ensure_future(self.monitor_website())

    async def shutdown(self):
        await self.session.close()

    async def start(self):
        await self._on_start()

        while not self.__is_running:
            try:
                await self._run()

            except aiohttp.client_exceptions.ClientConnectorError:
                self.logger.exception("Error connecting to telegram services", exc_info=True)

                await asyncio.sleep(Config.RECONNECT_TO_TG_SLEEP_TIME)
                await self.shutdown()

            else:
                self.__is_running = True

                self.logger.info("Healthchecker bot started for %s", self.monitoring_resource.name)

    async def _actualize_last_update_id(self, update_id: int):
        self.last_update_id = update_id

        with open(Config.CURRENT_UPDATE_ID_FILE_NAME, "w") as f:
            f.write(str(update_id))

    async def _add_user(self, user: User):
        self.__users.append(user)

        if not user.exist:
            user.save()

        self.logger.info("User added: %s\nCurrent chats: %s", user, self.__users)

    async def _delete_user(self, user):
        if user in self.__users:
            self.__users.remove(user)
        else:
            self.logger.warning("Removing not existing user from app: %s", user)

        if user.exist:
            user.delete()
        else:
            self.logger.warning("Removing not existing user from folder: %s", user)

        self.logger.info("User deleted: %s\nCurrent chats: %s", user, self.__users)

    async def answer(self, update):
        try:
            received_msg = update["message"]
            user_dict = received_msg["from"]
            user_chat_id = received_msg["chat"]["id"]
            user = User(
                tg_id=user_dict["id"],
                first_name=user_dict["first_name"],
                last_name=user_dict["last_name"],
                username=user_dict["username"],
                current_chat_id=user_chat_id
            )

        except KeyError as e:
            self.logger.warning(f"Update {str(e)}: {update}", exc_info=True)
            return None

        if user not in self.__users:
            await self._add_user(user)
        if not user.exist:
            user.save()
        else:
            # работаем с юзером, который есть в списке
            for existing_user in self.__users:
                if existing_user == user:
                    user = existing_user

        resp_text = None

        if received_msg["text"].strip() == "/start":
            user.receiving_updates = True
            user.update()
            resp_text = "You have started to receive SportNote state notifications"

        if received_msg["text"].strip() == "/status":
            resp_text = f"Requested status:\n{self.monitoring_resource.create_current_state_report()}"

        if received_msg["text"].strip() == "/stop":
            user.receiving_updates = False
            user.update()
            resp_text = "You will no longer receive SportNote state notifications"

        if resp_text:
            msg = json.dumps({"chat_id": user.current_chat_id, "text": resp_text})

            async with self.session.post(
                    f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                    data=msg,
                    headers={"Content-Type": "application/json"}
            ) as resp:
                return resp

        return None

    async def receive_updates(self):
        self.__is_receiving_updates = True

        self.logger.info("Started to recieve tg updates")

        while True:
            async with self.session.get(
                f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getUpdates?offset={self.last_update_id + 1}"
            ) as resp:
                resp_json = await resp.json()

                if resp_json["ok"]:
                    updates = resp_json["result"]

                    if updates:
                        await self._actualize_last_update_id(updates[-1]["update_id"])

                        # отвечаем на сообщения
                        answers = [asyncio.create_task(self.answer(update)) for update in updates]
                        results = await asyncio.gather(*answers)

                        await asyncio.sleep(Config.UPDATES_RECEIVE_FREQUENCY)
                else:
                    self.logger.warning("Not ok response: %s", resp)

                    await asyncio.sleep(Config.UPDATES_RECEIVE_FREQUENCY)

                    continue

    async def monitor_website(self):
        self.logger.info("Started to monitor %s", self.monitoring_resource.url)

        while True:
            try:
                async with self.session.get(self.monitoring_resource.url) as resp:
                    self.monitoring_resource.update_status_code(resp.status)

                    self.logger.debug(
                        "Status code for %s: %s",
                        self.monitoring_resource.url,
                        self.monitoring_resource.current_status_code
                    )

                    if not self.__is_monitoring:
                        self.__is_monitoring = True

            except aiohttp.client_exceptions.ClientConnectorError as e:
                self.logger.error(str(e), exc_info=True)
                self.__is_monitoring = False

            else:
                await asyncio.sleep(Config.PING_FREQUENCY)

    @property
    def notified_users(self):
        return [user for user in self.__users if user.receiving_updates]

    async def send_notifications(self):
        # ждем пока не начнем мониторить и получать апдейты от тг
        while not (self.__is_monitoring and self.__is_receiving_updates):
            await asyncio.sleep(1)
        else:
            self.logger.info(
                "Starting to send notifications to %s",
                self.notified_users
            )
            self.__is_sending_notifications = True

        while True:
            if self.__is_monitoring and self.__is_receiving_updates:
                for user in self.notified_users:
                    async with self.session.post(
                        f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage",
                        data=json.dumps(
                            {
                                "chat_id": user.current_chat_id,
                                "text": self.monitoring_resource.create_current_state_report()
                            }
                        ),
                        headers={"Content-Type": "application/json"}
                    ) as resp:
                        self.logger.debug("Notification sent to %s", user)
            else:
                self.__is_sending_notifications = False

            sleep_time = Config.WEBSITE_DOWN_SLEEP_TIME

            if self.monitoring_resource.is_running:
                sleep_time = Config.WEBSITE_UP_SLEEP_TIME

            await asyncio.sleep(sleep_time)
